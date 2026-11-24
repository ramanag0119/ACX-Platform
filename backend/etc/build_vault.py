r"""Create, re-key or reset the HMS credential vault in `backend/etc/`.

    .venv\Scripts\python.exe etc\build_vault.py            create if missing
    .venv\Scripts\python.exe etc\build_vault.py --rekey    change the master password
    .venv\Scripts\python.exe etc\build_vault.py --reset    rebuild an unopenable vault

Two files live next to this script:

    hmsBackend.kdbx   the KeePass vault the application reads at startup
    shibboleth.zip    holds shibboleth.txt, whose single line is the vault's
                      MASTER PASSWORD

THE ONE RULE: the vault's master key and the text in the ZIP must change
TOGETHER. Editing shibboleth.txt on its own does NOT re-key the vault -- the
ZIP is only where the password is *stored*. Do that and the vault becomes
unopenable, because its real key is whatever the ZIP used to say. Use --rekey,
which changes both in a single step, and the two can never drift apart.

    --rekey   prompts for the new master password, opens the vault with the
              password currently in the ZIP, re-keys it, then rewrites the ZIP.
              Requires the vault to still be openable.

    --reset   for a vault that is ALREADY unopenable. Moves it aside to
              *.unopenable-<n>.bak (never deletes) and builds a fresh vault
              keyed to whatever the ZIP currently says. Any password stored in
              the old vault is lost -- it cannot be read without its key.

Plain creation prefills host / port / user / database and leaves the PASSWORD
EMPTY, for a human to set in KeePass.
"""

from __future__ import annotations

import argparse
import getpass
import secrets
import sys
import zipfile
from pathlib import Path

try:
    from pykeepass import PyKeePass, create_database
    from pykeepass.exceptions import CredentialsError
except ImportError:
    sys.exit(
        "pykeepass is not installed. Run:\n"
        r"  .venv\Scripts\python.exe -m pip install pykeepass"
    )

HERE = Path(__file__).resolve().parent
VAULT = HERE / "hmsBackend.kdbx"
ZIP = HERE / "shibboleth.zip"
INNER = "shibboleth.txt"

ENTRY_TITLE = "MYSQL_BSS"

#: Non-secret deployment coordinates, prefilled so the only thing a human has
#: to type into KeePass is the password itself.
DEFAULTS = {
    "host": "192.168.0.120",
    "port": "3306",
    "username": "inspironics_app",
    "database": "inspironics_app",
}


def read_zip_password() -> str:
    """The master password currently stored in the ZIP.

    Matches the inner file by basename at any depth: re-zipping a folder nests
    it as `shibboleth/shibboleth.txt`, and that must not break anything.
    """
    if not ZIP.is_file():
        sys.exit(f"No {ZIP.name} at {ZIP}")
    with zipfile.ZipFile(ZIP) as z:
        files = [n for n in z.namelist() if not n.endswith("/")]
        wanted = INNER.lower()
        match = next((n for n in files if Path(n).name.lower() == wanted), None)
        if match is None:
            sys.exit(f"{ZIP.name} does not contain {INNER}. Files found: {files}")
        return z.read(match).decode("utf-8").rstrip("\r\n")


def write_zip_password(password: str) -> None:
    """Store `password` in the ZIP, flat at the root."""
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(INNER, password)


def seed_entry(kp: PyKeePass) -> None:
    entry = kp.add_entry(
        kp.root_group,
        title=ENTRY_TITLE,
        username=DEFAULTS["username"],
        password="",  # filled in by a human, in KeePass
        url=DEFAULTS["host"],
    )
    entry.set_custom_property("Port", DEFAULTS["port"])
    entry.set_custom_property("Database", DEFAULTS["database"])
    kp.save()


def prompt_new_password() -> str:
    """Ask twice, never echo, never accept an empty value."""
    for _ in range(3):
        first = getpass.getpass("New vault master password: ")
        if not first:
            print("  Empty password. Try again.")
            continue
        if first != getpass.getpass("Confirm: "):
            print("  They do not match. Try again.")
            continue
        return first
    sys.exit("Giving up.")


def backup_path() -> Path:
    """An unused *.unopenable-<n>.bak name, so a reset never overwrites."""
    n = 1
    while (p := VAULT.with_suffix(f".kdbx.unopenable-{n}.bak")).exists():
        n += 1
    return p


def do_create() -> int:
    if VAULT.exists():
        print(f"Vault already exists, leaving it untouched: {VAULT}")
        print("To change its master password:  etc\\build_vault.py --rekey")
        print("If it will no longer open:      etc\\build_vault.py --reset")
        return 0

    # Generated here and written straight to the ZIP -- never printed, so it
    # cannot land in terminal scrollback or a CI log.
    master = secrets.token_urlsafe(32)
    create_database(str(VAULT), password=master)
    seed_entry(PyKeePass(str(VAULT), password=master))
    write_zip_password(master)
    del master

    print(f"Created {VAULT}")
    print(f"Created {ZIP}  (contains {INNER})")
    _print_next_steps()
    return 0


def do_rekey() -> int:
    if not VAULT.exists():
        sys.exit(f"No vault at {VAULT}. Run without arguments to create one.")

    current = read_zip_password()
    try:
        kp = PyKeePass(str(VAULT), password=current)
    except CredentialsError:
        sys.exit(
            f"The password in {ZIP.name} does not open {VAULT.name}, so the "
            "vault cannot be re-keyed.\n"
            "This is what happens when shibboleth.txt is edited by hand: the "
            "vault keeps its OLD key.\n"
            f"If the old password is gone, rebuild with:  etc\\{Path(__file__).name} --reset"
        )
    del current

    new = prompt_new_password()
    kp.password = new
    kp.save()
    write_zip_password(new)
    del new

    print(f"Re-keyed {VAULT.name} and updated {ZIP.name}. They are in sync.")
    return 0


def do_set_password() -> int:
    """Set the MYSQL_BSS password without going through the KeePass GUI.

    Exists because editing an entry in KeePass only changes it in memory --
    the .kdbx is not written until the database itself is saved, which is easy
    to miss. This prompts, writes and saves in one step, so there is no
    separate save to forget.
    """
    if not VAULT.exists():
        sys.exit(f"No vault at {VAULT}. Run without arguments to create one.")

    master = read_zip_password()
    try:
        kp = PyKeePass(str(VAULT), password=master)
    except CredentialsError:
        sys.exit(
            f"The password in {ZIP.name} does not open {VAULT.name}.\n"
            f"If the vault was re-keyed in KeePass, rebuild with:  --reset"
        )
    del master

    entry = kp.find_entries(title=ENTRY_TITLE, first=True)
    if entry is None:
        sys.exit(f"The vault has no entry titled '{ENTRY_TITLE}'.")

    for _ in range(3):
        first = getpass.getpass(f"MySQL password for {entry.username}@{entry.url}: ")
        if not first:
            print("  Empty password. Try again.")
            continue
        if first != getpass.getpass("Confirm: "):
            print("  They do not match. Try again.")
            continue
        entry.password = first
        kp.save()
        del first
        print(f"\nSaved. '{ENTRY_TITLE}' now holds a password ({len(entry.password)} chars).")
        print("Verify with:")
        print(r"    .venv\Scripts\python.exe -m scripts.verify_mysql_connection")
        return 0
    sys.exit("Giving up.")


def do_reset() -> int:
    master = read_zip_password()

    if VAULT.exists():
        try:
            PyKeePass(str(VAULT), password=master)
        except CredentialsError:
            pass
        else:
            sys.exit(
                f"{VAULT.name} opens fine with the password in {ZIP.name}; "
                "there is nothing to reset.\n"
                "To change the master password, use --rekey."
            )
        backup = backup_path()
        VAULT.rename(backup)
        print(f"Moved the unopenable vault to {backup.name} (not deleted).")

    create_database(str(VAULT), password=master)
    seed_entry(PyKeePass(str(VAULT), password=master))
    del master

    print(f"Rebuilt {VAULT.name}, keyed to the password already in {ZIP.name}.")
    _print_next_steps()
    return 0


def _print_next_steps() -> None:
    print()
    print(f"Entry '{ENTRY_TITLE}' is prefilled with:")
    for k, v in DEFAULTS.items():
        print(f"    {k:<9} {v}")
    print("    password  <EMPTY -- set this yourself>")
    print()
    print(f"Open {VAULT.name} in KeePass using the password inside {ZIP.name},")
    print(f"set the password on '{ENTRY_TITLE}', and save. Then verify with:")
    print(r"    .venv\Scripts\python.exe -m scripts.verify_mysql_connection")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--set-password", action="store_true",
                       help="set the MYSQL_BSS password (prompts; no KeePass needed)")
    group.add_argument("--rekey", action="store_true",
                       help="change the master password (vault + ZIP together)")
    group.add_argument("--reset", action="store_true",
                       help="rebuild a vault that no longer opens")
    args = parser.parse_args()

    if args.set_password:
        return do_set_password()
    if args.rekey:
        return do_rekey()
    if args.reset:
        return do_reset()
    return do_create()


if __name__ == "__main__":
    raise SystemExit(main())
