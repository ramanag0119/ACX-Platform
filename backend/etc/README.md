# `backend/etc/` — runtime credential store

The BSS MySQL credentials live here, in a KeePass vault. **They are not in
`.env`.** `.env` holds only non-secret application settings; nothing in it can
reach the database.

| File | Tracked in git? | What it is |
|---|---|---|
| `hmsBackend.kdbx` | **no** | the vault; entry `MYSQL_BSS` holds host, port, user, password, database |
| `shibboleth.zip` | **no** | contains `shibboleth.txt`, whose single line is the vault's master password |
| `build_vault.py` | yes | creates / re-keys / resets both files; never overwrites an existing vault |
| `README.md` | yes | this file |

## Changing the master password

**Do not edit `shibboleth.txt` by hand.** The ZIP is only where the password is
*stored* — editing it does not re-key the vault, which keeps its old key and
then refuses to open with what you just typed.

Use the command that changes both together:

```
.venv\Scripts\python.exe etc\build_vault.py --rekey
```

It prompts for the new password (twice, never echoed), re-keys the vault, and
rewrites the ZIP. The two can't drift apart.

If a vault is *already* unopenable because the ZIP was hand-edited:

```
.venv\Scripts\python.exe etc\build_vault.py --reset
```

That moves the old vault to `*.unopenable-<n>.bak` (never deletes) and builds a
fresh one keyed to whatever the ZIP currently says. **Any password stored in
the old vault is lost** — without its key it cannot be read.

## First-time setup

```
.venv\Scripts\python.exe etc\build_vault.py
```

This creates the vault with `MYSQL_BSS` prefilled — host `192.168.0.120`,
port `3306`, user `inspironics_app`, database `inspironics_app` — and the
password **deliberately empty**.

Then:

1. Unzip `shibboleth.zip` and read `shibboleth.txt`. That line is the vault's
   master password.
2. Open `hmsBackend.kdbx` in KeePass with it.
3. Set the **Password** on the `MYSQL_BSS` entry. Correct any of host (the
   **URL** field), **Port** or **Database** if the deployment differs.
4. Save and close.

Verify:

```
.venv\Scripts\python.exe -m scripts.verify_mysql_connection
```

Every line `PASS` and exit code 0 means the backend is connected.

## How the application reads it

`app/core/vault.py` resolves the master password in this order:

1. `etc/shibboleth.zip` → `shibboleth.txt` — the normal path
2. `HMS_VAULT_MASTER_PASSWORD` in the environment — CI and containers, where
   shipping the zip is not appropriate
3. an interactive prompt — a workstation with no zip present

`app/core/config.py` then exposes `settings.MYSQL_HOST`, `MYSQL_PORT`,
`MYSQL_USER`, `MYSQL_PASSWORD` and `MYSQL_DATABASE` as properties backed by
that entry, cached once per process. Call sites did not change.

## What this does and does not protect against

`shibboleth.zip` is a plain ZIP, so **anyone who can read this directory can
read the master password and therefore the vault.** This is not a defence
against someone already on the machine, and it is not a reason to relax how
`etc/` is handled.

What it does buy: the credential exists in exactly one encrypted file instead
of being scattered across `.env` files, shell history, terminal scrollback and
screenshots; and rotating it is a single edit in one place.

Keep `etc/` off shared drives and out of backups that leave the machine. Both
secret files are gitignored — verify with
`git check-ignore -v backend/etc/hmsBackend.kdbx`.

## TLS

The connection is **encrypted and the server certificate is verified**
(`MYSQL_SSL_VERIFY_CERT=true`, verified 2026-11-13).

The CA bundle **path** is the fourth property on the `MYSQL_BSS` entry:

| Property | Example |
|---|---|
| `SSL_CA_Path` | `D:\Inspornics\ACX codes\HMS-Security\Certificates\ca.pem` |

It lives in the vault beside the credential it protects so that the host, the
login and the trust anchor for that host are rotated in one place. A path is
not itself a secret, but splitting it from the host it applies to is how the
two drift apart. The **bundle file must stay outside this repository** — only
the path is recorded here.

`MYSQL_SSL_CA` in `.env` remains an override for a machine whose bundle sits
somewhere else; leave it empty and the vault value is used. The on/off switches
(`MYSQL_SSL_VERIFY_CERT`, `MYSQL_SSL_VERIFY_IDENTITY`) stay in `.env` because
they are policy, not secrets.

If the path is wrong, startup fails with an explicit
`MYSQL_SSL_CA points at '...', which is not a file` rather than an SSL
handshake error — a missing bundle must not be mistakable for an untrusted
server.

### Hostname verification is ON

`MYSQL_SSL_VERIFY_IDENTITY=true`. The server's leaf certificate
(`CN=mysql.inspironicsindia.in`) carries
`subjectAltName = DNS:mysql.inspironicsindia.in, IP:183.82.242.65,
IP:192.168.0.120`, so it names the LAN address HMS actually connects on and
the identity check succeeds (verified 2026-11-16, cipher
`TLS_AES_256_GCM_SHA384`).

This was previously off: the certificate carried only the public identity, and
an identity check failed with `CERTIFICATE_VERIFY_FAILED`. The DBA has since
reissued it with `IP:192.168.0.120` added to the SAN, which removed the
limitation.

Verifying the chain without also checking *who* the certificate names would
accept any host holding some other certificate from the same CA, so the two
switches belong on together. If a future host is reached by a name or address
its certificate does not carry, fix the certificate rather than turning this
off.
