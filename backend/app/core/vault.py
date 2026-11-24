"""KeePass credential provider for the BSS MySQL connection.

The BSS credentials live in `backend/etc/hmsBackend.kdbx`, NOT in `.env`.
`.env` keeps only non-secret application settings; anything that would let
someone reach the database comes from the vault.

Master password resolution, in order:

    1. `etc/shibboleth.zip` -> `shibboleth.txt` (the normal path; mirrors the
       IoT backend so one pattern covers both services)
    2. `HMS_VAULT_MASTER_PASSWORD` in the environment (CI, containers)
    3. an interactive prompt (developer workstation, no zip present)

SECURITY RULES, enforced below:
  * the master password exists only as a local in `_master_password()` and the
    local in `open_vault()`; it is never stored on an object and never logged;
  * the entry password is returned to the caller and never logged;
  * a wrong master password produces a generic error -- the vault's internal
    state is never described.

A note on what this does and does not buy you: shibboleth.zip is a plain ZIP,
so anyone who can read `etc/` can read the master password. This is not
protection against someone already on the box -- it exists so the credential
is in ONE encrypted file instead of scattered through `.env` files, terminal
history and screenshots, and so rotating it is a single edit. Keep `etc/` off
shared drives and out of git (it is gitignored).
"""

from __future__ import annotations

import getpass
import logging
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("hms.vault")

#: backend/app/core/vault.py -> backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]
ETC_DIR = BACKEND_DIR / "etc"
VAULT_PATH = ETC_DIR / "hmsBackend.kdbx"
ZIP_PATH = ETC_DIR / "shibboleth.zip"
ZIP_INNER = "shibboleth.txt"

#: Entry holding the BSS MySQL credentials.
MYSQL_ENTRY_TITLE = "MYSQL_BSS"

ENV_MASTER_PASSWORD = "HMS_VAULT_MASTER_PASSWORD"


class VaultError(RuntimeError):
    """The vault could not be opened or did not hold what was asked for."""


@dataclass(frozen=True)
class MySQLCredentials:
    """What the vault knows about reaching the BSS database."""

    host: str
    port: int
    username: str
    password: str
    database: str
    #: Absolute path to the PEM CA bundle that signed the server certificate,
    #: from the entry's `SSL_CA_Path` property. Empty when the entry does not
    #: carry one. The path itself is not a secret -- it lives beside the
    #: credential so host, port and the trust anchor for that host are rotated
    #: together, in one place, instead of drifting apart across `.env` files.
    ssl_ca: str = ""


def _read_text_from_zip(zip_path: Path, inner: str | None = None) -> str:
    """Read the master password out of the ZIP.

    The inner file is matched by BASENAME anywhere in the archive, because
    re-zipping a folder in Explorer (or `zip -r`) nests it as
    `shibboleth/shibboleth.txt` rather than leaving it at the root. Requiring
    the exact root path turned an ordinary re-zip into an unopenable vault, so
    any depth is accepted.
    """
    with zipfile.ZipFile(zip_path, "r") as z:
        files = [n for n in z.namelist() if not n.endswith("/")]
        if not files:
            raise VaultError(f"{zip_path.name} contains no files.")

        if inner is None:
            match = files[0]
        else:
            wanted = Path(inner).name.lower()
            candidates = [n for n in files if Path(n).name.lower() == wanted]
            if not candidates:
                raise VaultError(
                    f"{zip_path.name} does not contain {inner} at any depth.\n"
                    f"Files found: {files}"
                )
            match = candidates[0]

        with z.open(match) as f:
            text = f.read().decode("utf-8")

    # Only strip trailing newlines a text editor adds. Leading/trailing spaces
    # could be deliberate characters in a password, so they are preserved.
    return text.rstrip("\r\n")


def _master_password() -> str:
    """Resolve the master password. Never logged, never returned to a caller."""
    if ZIP_PATH.is_file():
        logger.info("Vault master password sourced from %s.", ZIP_PATH.name)
        return _read_text_from_zip(ZIP_PATH, ZIP_INNER)

    from_env = os.environ.get(ENV_MASTER_PASSWORD)
    if from_env:
        logger.info("Vault master password sourced from %s.", ENV_MASTER_PASSWORD)
        return from_env

    logger.info("Vault master password not found; prompting interactively.")
    return getpass.getpass("HMS vault master password: ")


def open_vault():
    """Open the vault and return the PyKeePass handle."""
    try:
        from pykeepass import PyKeePass
        from pykeepass.exceptions import CredentialsError
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise VaultError(
            "pykeepass is not installed. Run: pip install -r requirements.txt"
        ) from exc

    if not VAULT_PATH.is_file():
        raise VaultError(
            f"No credential vault at {VAULT_PATH}.\n"
            r"Create it with:  .venv\Scripts\python.exe etc\build_vault.py"
        )

    master = _master_password()
    try:
        return PyKeePass(str(VAULT_PATH), password=master)
    except CredentialsError as exc:
        # Deliberately generic: never describe the vault's state.
        raise VaultError(
            f"Could not unlock {VAULT_PATH.name}. The master password in "
            f"{ZIP_PATH.name} does not match this vault."
        ) from exc
    finally:
        del master


def get_mysql_credentials() -> MySQLCredentials:
    """Read the BSS MySQL credentials out of the vault.

    Raises `VaultError` with an actionable message when the vault, the entry
    or the password is missing -- the caller turns that into a startup failure
    rather than silently falling back to an unconfigured connection.
    """
    kp = open_vault()
    entry = kp.find_entries(title=MYSQL_ENTRY_TITLE, first=True)
    if entry is None:
        titles = sorted(e.title for e in kp.entries if e.title)
        raise VaultError(
            f"The vault has no entry titled '{MYSQL_ENTRY_TITLE}'.\n"
            f"Entries found: {titles or '(none)'}"
        )
    if not entry.password:
        raise VaultError(
            f"Entry '{MYSQL_ENTRY_TITLE}' exists but its password is empty.\n"
            "Open the vault in KeePass, set the password, and save."
        )

    def prop(name: str, fallback: str) -> str:
        value = entry.get_custom_property(name)
        return value if value else fallback

    port_raw = prop("Port", "3306")
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise VaultError(
            f"Entry '{MYSQL_ENTRY_TITLE}' has a non-numeric Port: {port_raw!r}"
        ) from exc

    host = entry.url or ""
    if not host:
        raise VaultError(
            f"Entry '{MYSQL_ENTRY_TITLE}' has no URL. Put the database host "
            "(e.g. 192.168.0.120) in the entry's URL field."
        )

    return MySQLCredentials(
        host=host,
        port=port,
        username=entry.username or "",
        password=entry.password,
        database=prop("Database", "inspironics_app"),
        # Absent is a valid state: an entry with no SSL_CA_Path means no trust
        # anchor is on file, which `config.mysql_ssl_args` then reports rather
        # than silently downgrading the connection.
        ssl_ca=prop("SSL_CA_Path", ""),
    )
