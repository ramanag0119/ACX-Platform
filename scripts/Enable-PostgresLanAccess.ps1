<#
.SYNOPSIS
    Enables LAN access to an EXISTING PostgreSQL instance on this machine.

.DESCRIPTION
    Data-safe by design. This script NEVER creates, drops, or modifies any
    database, schema, table, row, role, or password. It never connects with psql
    and never runs SQL. hms_db is not opened at all.

    It only touches:
      - postgresql.conf   listen_addresses, and only if it is loopback-only
      - pg_hba.conf       appends one host rule for the given subnet, if missing
      - Windows Firewall  adds one inbound rule scoped to the given subnet
      - the PostgreSQL service  reload, or restart only if listen_addresses changed

    Both config files are backed up next to the original with a timestamp
    before any edit. If a setting is already correct, it is left untouched.

.PARAMETER Subnet
    CIDR allowed to connect. Default 192.168.0.0/24.

.PARAMETER Port
    PostgreSQL port to configure. Default 5432.

.PARAMETER AuthMethod
    pg_hba method for the new rule. 'auto' matches the cluster's existing local
    rules, else scram-sha-256 on PG 14+ and md5 on older.

.PARAMETER DryRun
    Report every change that would be made, write nothing, exit.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Enable-PostgresLanAccess.ps1 -DryRun
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Enable-PostgresLanAccess.ps1
#>

[CmdletBinding()]
param(
    [string] $Subnet = '192.168.0.0/24',
    [int]    $Port   = 5432,
    [ValidateSet('auto', 'scram-sha-256', 'md5', 'trust', 'password')]
    [string] $AuthMethod = 'auto',
    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'

$script:Changed      = @()
$script:Skipped      = @()
$script:Problems     = @()
$script:NeedsRestart = $false
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

function Say  ($m) { Write-Host $m }
function Step ($m) { Write-Host ''; Write-Host "== $m" -ForegroundColor Cyan }
function Ok   ($m) { Write-Host "   [ok]   $m" -ForegroundColor Green }
function Info ($m) { Write-Host "   [info] $m" -ForegroundColor Gray }
function Warn ($m) { Write-Host "   [warn] $m" -ForegroundColor Yellow }
function Fail ($m) { Write-Host "   [FAIL] $m" -ForegroundColor Red }
function Nz   ($v, $alt) { if ($null -ne $v -and "$v" -ne '') { "$v" } else { $alt } }

# ------------------------------------------------------------- elevation
Step 'Checking privileges'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin  = (New-Object Security.Principal.WindowsPrincipal($identity)).IsInRole(
                [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Fail 'This must run in an ELEVATED PowerShell window.'
    Fail 'Close this window, right-click PowerShell > Run as administrator, then re-run.'
    exit 1
}
Ok 'Running as administrator.'

# --------------------------------------------------- detect installation
Step 'Detecting PostgreSQL installation'

$installs = New-Object System.Collections.ArrayList

foreach ($root in 'HKLM:\SOFTWARE\PostgreSQL\Installations',
                  'HKLM:\SOFTWARE\WOW6432Node\PostgreSQL\Installations') {
    if (Test-Path $root) {
        foreach ($key in Get-ChildItem $root) {
            $p = Get-ItemProperty $key.PSPath
            [void]$installs.Add([pscustomobject]@{
                Version     = $p.Version
                BaseDir     = $p.'Base Directory'
                DataDir     = $p.'Data Directory'
                ServiceName = $p.'Service ID'
                Source      = 'registry'
            })
        }
    }
}

# Services are the authoritative view of what can actually listen.
$svcs = @(Get-CimInstance Win32_Service -Filter "Name LIKE 'postgres%'" -ErrorAction SilentlyContinue)
foreach ($s in $svcs) {
    $svcData = $null
    if     ($s.PathName -match '-D\s+"([^"]+)"') { $svcData = $Matches[1] }
    elseif ($s.PathName -match '-D\s+(\S+)')     { $svcData = $Matches[1].Trim('"') }

    $svcBin = $null
    if ($s.PathName -match '"?([A-Za-z]:\\.*?\\bin)\\pg_ctl\.exe') { $svcBin = $Matches[1] }

    $known = $installs | Where-Object { $_.ServiceName -eq $s.Name } | Select-Object -First 1
    if ($known) {
        if (-not $known.DataDir -and $svcData) { $known.DataDir = $svcData }
        if (-not $known.BaseDir -and $svcBin)  { $known.BaseDir = (Split-Path $svcBin -Parent) }
    }
    else {
        [void]$installs.Add([pscustomobject]@{
            Version     = $null
            BaseDir     = if ($svcBin) { Split-Path $svcBin -Parent } else { $null }
            DataDir     = $svcData
            ServiceName = $s.Name
            Source      = 'service'
        })
    }
}

if ($installs.Count -eq 0) {
    # Last resort: the standard EDB installer layout on disk.
    foreach ($glob in 'C:\Program Files\PostgreSQL\*', 'C:\Program Files (x86)\PostgreSQL\*') {
        foreach ($d in (Get-ChildItem $glob -Directory -ErrorAction SilentlyContinue)) {
            [void]$installs.Add([pscustomobject]@{
                Version     = $d.Name
                BaseDir     = $d.FullName
                DataDir     = (Join-Path $d.FullName 'data')
                ServiceName = $null
                Source      = 'filesystem'
            })
        }
    }
}

if ($installs.Count -eq 0) {
    Fail 'No PostgreSQL installation found (checked registry, services, Program Files).'
    Fail 'Install PostgreSQL on this machine first, then re-run this script.'
    exit 2
}

foreach ($i in $installs) {
    Info ('found: version={0} service={1} data={2} [{3}]' -f (Nz $i.Version '?'),
          (Nz $i.ServiceName 'none'), (Nz $i.DataDir '?'), $i.Source)
}

# --------------------------------------- pick the cluster on the port
Step "Identifying the cluster configured for port $Port"

function Get-ClusterPort([string] $dir) {
    # A running cluster records its real port on line 4 of postmaster.pid.
    $pidFile = Join-Path $dir 'postmaster.pid'
    if (Test-Path $pidFile) {
        $lines = @(Get-Content $pidFile -ErrorAction SilentlyContinue)
        if ($lines.Count -ge 4 -and $lines[3] -match '^\s*(\d+)\s*$') { return [int]$Matches[1] }
    }
    $conf = Join-Path $dir 'postgresql.conf'
    if (Test-Path $conf) {
        $m = @(Select-String -Path $conf -Pattern '^\s*port\s*=\s*(\d+)' -ErrorAction SilentlyContinue)
        if ($m.Count -gt 0) { return [int]$m[-1].Matches[0].Groups[1].Value }
    }
    return 5432   # compiled-in default
}

$target = $null
foreach ($i in $installs) {
    if (-not $i.DataDir) { continue }
    if (-not (Test-Path (Join-Path $i.DataDir 'postgresql.conf'))) {
        Info ('skipping {0} (no postgresql.conf)' -f $i.DataDir)
        continue
    }
    $found = Get-ClusterPort $i.DataDir
    Info ('cluster {0} -> port {1}' -f $i.DataDir, $found)
    if ($found -eq $Port) { $target = $i; break }
}

if (-not $target) {
    Fail "No cluster on this machine is configured for port $Port. Nothing was changed."
    Fail 'Re-run with -Port <actual port> if this machine uses a different one.'
    exit 3
}

$dataDir  = $target.DataDir
$confFile = Join-Path $dataDir 'postgresql.conf'
$hbaFile  = Join-Path $dataDir 'pg_hba.conf'
$svcName  = $target.ServiceName
$binDir   = if ($target.BaseDir) { Join-Path $target.BaseDir 'bin' } else { $null }
Ok "Target cluster: $dataDir  (service: $(Nz $svcName 'unknown'))"

# pg_hba.conf can be relocated by hba_file
$hbaSet = @(Select-String -Path $confFile -Pattern "^\s*hba_file\s*=\s*'([^']+)'" -ErrorAction SilentlyContinue)
if ($hbaSet.Count -gt 0) {
    $hbaFile = $hbaSet[-1].Matches[0].Groups[1].Value
    Info "hba_file override in postgresql.conf: $hbaFile"
}
if (-not (Test-Path $hbaFile)) {
    Fail "pg_hba.conf not found at $hbaFile - nothing changed."
    exit 4
}

$serverMajor = $null
$pgVersionFile = Join-Path $dataDir 'PG_VERSION'
if (Test-Path $pgVersionFile) {
    $raw = (Get-Content $pgVersionFile -Raw).Trim()
    $serverMajor = [int]($raw.Split('.')[0])
    Info "Server major version: $serverMajor"
}

function Backup-File([string] $path) {
    $bak = "$path.bak-$stamp"
    if (-not $DryRun) { Copy-Item -LiteralPath $path -Destination $bak -Force }
    Info "backup: $bak"
}

# --------------------------------------------------- listen_addresses
Step 'Checking listen_addresses'

$confLines = @(Get-Content -LiteralPath $confFile)
$listenIdx = -1
$listenVal = $null
for ($n = 0; $n -lt $confLines.Count; $n++) {
    if ($confLines[$n] -match "^\s*listen_addresses\s*=\s*'?([^'#]*)'?") {
        $listenIdx = $n
        $listenVal = $Matches[1].Trim()
    }
}

$lanIPs = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -notlike '127.*' } | ForEach-Object { $_.IPAddress })

$listenOk = $false
if ($listenIdx -ge 0) {
    Info "current: listen_addresses = '$listenVal'"
    $parts = @($listenVal -split ',' | ForEach-Object { $_.Trim() })
    if ($parts -contains '*' -or $parts -contains '0.0.0.0') { $listenOk = $true }
    elseif (@($parts | Where-Object { $lanIPs -contains $_ }).Count -gt 0) { $listenOk = $true }
}
else {
    Info "listen_addresses not set explicitly - PostgreSQL defaults to 'localhost'."
}

if ($listenOk) {
    Ok 'listen_addresses already accepts LAN connections. Leaving it unchanged.'
    $script:Skipped += 'postgresql.conf listen_addresses (already correct)'
}
else {
    Warn 'listen_addresses is loopback-only, so LAN clients are refused before auth.'
    Backup-File $confFile
    $newLine = "listen_addresses = '*'`t# set by Enable-PostgresLanAccess.ps1 $stamp"
    if ($listenIdx -ge 0) {
        $confLines[$listenIdx] = $newLine
        $outLines = $confLines
    }
    else {
        $outLines = $confLines + @('', "# added by Enable-PostgresLanAccess.ps1 $stamp", $newLine)
    }
    if (-not $DryRun) { Set-Content -LiteralPath $confFile -Value $outLines -Encoding ascii }
    Ok "listen_addresses = '*'   (pg_hba + firewall stay the real access control)"
    $script:Changed      += "postgresql.conf: listen_addresses = '*'"
    $script:NeedsRestart = $true    # postmaster-level: a reload will not pick this up
}

# ---------------------------------------------------------- pg_hba.conf
Step "Checking pg_hba.conf for $Subnet"

$hbaLines  = @(Get-Content -LiteralPath $hbaFile)
$hbaActive = @($hbaLines | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '\S' })

# Split each active rule into fields once, for the checks below.
$hbaRules = foreach ($line in $hbaActive) {
    $f = @($line -split '\s+' | Where-Object { $_ -ne '' })
    if ($f.Count -ge 4) { [pscustomobject]@{ Type = $f[0]; Addr = $f[3]; Method = $(if ($f.Count -ge 5) { $f[4] } else { $null }) } }
}
$hostTypes = @('host', 'hostssl', 'hostnossl')

$covered = @($hbaRules | Where-Object {
    $hostTypes -contains $_.Type -and
    ($_.Addr -eq $Subnet -or $_.Addr -eq '0.0.0.0/0' -or $_.Addr -eq 'all')
}).Count -gt 0

if ($AuthMethod -eq 'auto') {
    $localMethod = @($hbaRules | Where-Object {
        $hostTypes -contains $_.Type -and $_.Addr -like '127.*' -and
        @('scram-sha-256', 'md5') -contains $_.Method
    } | ForEach-Object { $_.Method } | Select-Object -First 1)

    if ($localMethod.Count -gt 0)                     { $AuthMethod = $localMethod[0] }
    elseif ($serverMajor -and $serverMajor -ge 14)    { $AuthMethod = 'scram-sha-256' }
    else                                              { $AuthMethod = 'md5' }
    Info "auth method resolved to: $AuthMethod"
}

if ($covered) {
    Ok "An existing host rule already covers $Subnet. Leaving pg_hba.conf unchanged."
    $script:Skipped += "pg_hba.conf (rule covering $Subnet already present)"
}
else {
    Warn "No active host rule covers $Subnet."
    Backup-File $hbaFile
    $newRule = "host    all             all             $Subnet          $AuthMethod"
    $append  = @(
        '',
        "# LAN access added by Enable-PostgresLanAccess.ps1 $stamp",
        '# TYPE  DATABASE        USER            ADDRESS                 METHOD',
        $newRule
    )
    if (-not $DryRun) { Add-Content -LiteralPath $hbaFile -Value $append -Encoding ascii }
    Ok "appended: $newRule"
    $script:Changed += "pg_hba.conf: $newRule"
}

# -------------------------------------------------------------- firewall
Step 'Checking Windows Firewall'

$ruleName = "PostgreSQL $Port (LAN $Subnet)"
$mine     = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

$otherRules = @()
try {
    $otherRules = @(Get-NetFirewallPortFilter -ErrorAction Stop |
        Where-Object { $_.Protocol -eq 'TCP' -and $_.LocalPort -contains "$Port" } |
        Get-NetFirewallRule -ErrorAction SilentlyContinue |
        Where-Object { $_.Direction -eq 'Inbound' -and $_.Action -eq 'Allow' -and $_.Enabled -eq 'True' })
}
catch { Info "could not enumerate existing firewall rules: $($_.Exception.Message)" }

if ($mine) {
    Ok "Firewall rule '$ruleName' already exists. Leaving it unchanged."
    $script:Skipped += 'firewall rule (already present)'
}
elseif ($otherRules.Count -gt 0) {
    Warn ("An inbound allow rule for TCP/{0} already exists: {1}" -f $Port,
          ((@($otherRules | Select-Object -First 3 | ForEach-Object { $_.DisplayName })) -join ', '))
    Info 'Not adding a duplicate. Check that rule is scoped to your LAN and not to Any.'
    $script:Skipped += "firewall rule (another inbound TCP/$Port allow rule exists)"
}
else {
    if (-not $DryRun) {
        New-NetFirewallRule -DisplayName $ruleName `
            -Description "Allow PostgreSQL from $Subnet only. Added $stamp." `
            -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port `
            -RemoteAddress $Subnet -Profile Any -Enabled True | Out-Null
    }
    Ok "created inbound TCP/$Port rule restricted to $Subnet"
    $script:Changed += "firewall: '$ruleName' (inbound TCP/$Port from $Subnet only)"
}

# ------------------------------------------------------ apply to server
Step 'Applying configuration to the running server'

$svcRunning = $false
if ($svcName) {
    $svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
    $svcRunning = ($svc -and $svc.Status -eq 'Running')
    Info "service $svcName status: $(if ($svc) { $svc.Status } else { 'not found' })"
}

if ($DryRun) {
    Info '-DryRun: no reload or restart performed.'
}
elseif ($script:Changed.Count -eq 0) {
    Info 'Nothing changed, so no reload is needed.'
}
elseif ($script:NeedsRestart) {
    Warn 'listen_addresses changed - that needs a full restart, a reload will not do.'
    if ($svcName -and $svcRunning) {
        Restart-Service -Name $svcName -Force
        Start-Sleep -Seconds 3
        Ok "restarted service $svcName"
    }
    elseif ($svcName) {
        Start-Service -Name $svcName
        Start-Sleep -Seconds 3
        Ok "started service $svcName"
    }
    else {
        Fail 'Service name unknown - restart PostgreSQL manually to apply listen_addresses.'
        $script:Problems += 'manual restart required'
    }
}
else {
    # Only pg_hba/firewall changed: a reload is enough and drops no connections.
    $reloaded = $false
    $pgctl = if ($binDir) { Join-Path $binDir 'pg_ctl.exe' } else { $null }
    if ($pgctl -and (Test-Path $pgctl) -and $svcRunning) {
        $out = & $pgctl reload -D "$dataDir" 2>&1
        if ($LASTEXITCODE -eq 0) { $reloaded = $true; Ok 'pg_ctl reload succeeded (no connections dropped)' }
        else { Info "pg_ctl reload failed: $out" }
    }
    if (-not $reloaded -and $svcName) {
        Restart-Service -Name $svcName -Force
        Start-Sleep -Seconds 3
        Ok "restarted service $svcName (reload was unavailable)"
    }
    elseif (-not $reloaded) {
        Fail 'Could not reload or restart automatically - restart PostgreSQL manually.'
        $script:Problems += 'manual reload required'
    }
}

# ---------------------------------------------------------- verification
Step 'Verifying that PostgreSQL is listening'

$listening = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listening.Count -eq 0) {
    Fail "Nothing is listening on TCP/$Port."
    if ($svcName) { Info "service status: $((Get-Service -Name $svcName).Status)" }
    $script:Problems += "no listener on TCP/$Port"
}
else {
    foreach ($l in ($listening | Sort-Object LocalAddress -Unique)) {
        Info ('listening on {0}:{1}' -f $l.LocalAddress, $l.LocalPort)
    }
    $wildcard = @($listening | Where-Object { $_.LocalAddress -eq '0.0.0.0' -or $_.LocalAddress -eq '::' })
    $onLan    = @($listening | Where-Object { $lanIPs -contains $_.LocalAddress })
    if ($wildcard.Count -gt 0 -or $onLan.Count -gt 0) {
        Ok 'PostgreSQL is bound to a LAN-reachable address.'
    }
    else {
        Fail 'PostgreSQL is bound to loopback only - LAN clients still cannot connect.'
        $script:Problems += 'loopback-only bind'
    }
}

# TCP handshake only: proves the listener accepts sockets. No login, no SQL.
$tcpOk = $false
try {
    $client = New-Object System.Net.Sockets.TcpClient
    $tcpOk  = $client.ConnectAsync('127.0.0.1', $Port).Wait(3000)
    $client.Close()
}
catch { $tcpOk = $false }
if ($tcpOk) { Ok "TCP connect to 127.0.0.1:$Port succeeded." }
else        { Warn "TCP connect to 127.0.0.1:$Port failed." }

# --------------------------------------------------------------- summary
Step 'Summary'
Say ''
Say "  Cluster data dir : $dataDir"
Say "  Service          : $(Nz $svcName 'unknown')"
Say "  Port             : $Port"
Say "  Allowed subnet   : $Subnet"
Say "  pg_hba method    : $AuthMethod"
Say ''
if ($script:Changed.Count -gt 0) {
    Say '  Changed:'
    foreach ($c in $script:Changed) { Say "    - $c" }
}
else { Say '  Changed: nothing - this machine was already configured.' }
if ($script:Skipped.Count -gt 0) {
    Say '  Left as-is:'
    foreach ($s in $script:Skipped) { Say "    - $s" }
}
Say ''
Say '  Not touched: no database, table, row, role, or password was created,'
Say '               dropped, or modified. No SQL was run and hms_db was never opened.'
Say ''
$hostLanIP = @($lanIPs | Where-Object { $_ -like ($Subnet.Split('/')[0].Substring(0, $Subnet.Split('/')[0].LastIndexOf('.') + 1) + '*') })
if ($hostLanIP.Count -gt 0) {
    Say "  Connect from another machine on the LAN using host: $($hostLanIP[0])  port: $Port"
}
elseif ($lanIPs.Count -gt 0) {
    Warn "This machine has no address inside $Subnet (its IPv4: $($lanIPs -join ', '))."
    Warn 'Re-run with -Subnet matching the real LAN range, or clients will be blocked.'
}

if ($DryRun) {
    Say ''
    Warn '-DryRun was set: NOTHING was written. Re-run without -DryRun to apply.'
}

if ($script:Problems.Count -gt 0) {
    Say ''
    Fail ('Unresolved: ' + ($script:Problems -join '; '))
    exit 5
}

Say ''
Ok 'Done.'
exit 0
