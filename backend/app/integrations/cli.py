"""Operator CLI for integration clients and credentials (never exposed over HTTP).

    python -m app.integrations.cli create-client  --code pms-hotel-a --protocol fias --actor ops.jane
    python -m app.integrations.cli enable-client  --code pms-hotel-a --actor ops.jane
    python -m app.integrations.cli disable-client --code pms-hotel-a --actor ops.jane
    python -m app.integrations.cli rotate-secret  --code pms-hotel-a --overlap-hours 24 --actor ops.jane
    python -m app.integrations.cli revoke-previous-secret --code pms-hotel-a --actor ops.jane

It uses the configured BSS database and needs the integration tables, which do
not exist until the candidate migration is approved (HF-39). A generated secret
is printed to stdout exactly once; deliver it through the channel approved under
HF-22 and never paste it into tickets or chat.
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta

from app.integrations.admin import IntegrationAdmin
from app.integrations.core.errors import IntegrationError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="app.integrations.cli", description="Integration client administration")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create-client")
    c.add_argument("--code", required=True)
    c.add_argument("--protocol", action="append", required=True, choices=["fias", "htng"])
    for name in ("enable-client", "disable-client", "revoke-previous-secret"):
        sub.add_parser(name).add_argument("--code", required=True)
    r = sub.add_parser("rotate-secret")
    r.add_argument("--code", required=True)
    r.add_argument("--overlap-hours", type=int, default=24)
    for sp in sub.choices.values():
        sp.add_argument("--actor", required=True, help="who is making the change (audited)")
    return p


def main(argv: list[str] | None = None, *, admin: IntegrationAdmin | None = None, out=sys.stdout) -> int:
    args = build_parser().parse_args(argv)
    if admin is None:  # pragma: no cover - production wiring
        from app.db.session import engine

        admin = IntegrationAdmin(engine)
    try:
        if args.command == "create-client":
            issued = admin.create_client(args.code, args.protocol, actor=args.actor)
            print(f"client {issued.client_code} created DISABLED; secret (shown once): {issued.secret}", file=out)
        elif args.command == "enable-client":
            admin.set_client_enabled(args.code, True, actor=args.actor)
            print(f"client {args.code} enabled", file=out)
        elif args.command == "disable-client":
            admin.set_client_enabled(args.code, False, actor=args.actor)
            print(f"client {args.code} disabled", file=out)
        elif args.command == "rotate-secret":
            issued = admin.rotate_secret(args.code, overlap=timedelta(hours=args.overlap_hours), actor=args.actor)
            until = issued.previous_valid_until.isoformat() if issued.previous_valid_until else "now (no overlap)"
            print(f"new secret (shown once): {issued.secret}; previous secret valid until {until}", file=out)
        elif args.command == "revoke-previous-secret":
            admin.revoke_previous_secret(args.code, actor=args.actor)
            print(f"previous secret of {args.code} revoked", file=out)
    except IntegrationError as exc:
        print(f"error: {exc.code}: {exc.message}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
