"""Certification CLI (test-only; run from backend/):

    python -m tests.integrations.certification list
    python -m tests.integrations.certification run [--id HTNG-SYN-001 ...] [--json out.json] [--md out.md]
    python -m tests.integrations.certification replay-vendor <contracts_dir> [--json out.json]
    python -m tests.integrations.certification compare run_a.json run_b.json

HMS scenarios need INTEGRATION_TEST_HMS_DB_URL (disposable DB); otherwise NOT RUN.
Exit code: 0 when no scenario FAILED, 1 otherwise. BLOCKED / NOT RUN are not failures
but are never reported as PASS.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from .core import load_all, run_scenarios
from .replay import replay_vendor_samples
from .report import build_report, compare, to_json, to_markdown


def main(argv: list[str] | None = None, out=sys.stdout) -> int:
    p = argparse.ArgumentParser(prog="tests.integrations.certification")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("--id", action="append")
    r.add_argument("--json")
    r.add_argument("--md")
    r.add_argument("--label", default="")
    v = sub.add_parser("replay-vendor")
    v.add_argument("contracts_dir")
    v.add_argument("--json")
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    args = p.parse_args(argv)

    if args.cmd == "list":
        for sc in load_all().values():
            print(f"{sc.id}\t{sc.protocol}\t{sc.category}\t{sc.description}", file=out)
        return 0
    if args.cmd == "run":
        known = load_all()
        unknown = [i for i in args.id or [] if i not in known]
        if unknown:
            print(f"unknown scenario id(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        report = build_report(run_scenarios(args.id), label=args.label)
        if args.json:
            pathlib.Path(args.json).write_text(to_json(report), encoding="utf-8")
        if args.md:
            pathlib.Path(args.md).write_text(to_markdown(report), encoding="utf-8")
        print(json.dumps(report["counts"]), file=out)
        return 1 if report["counts"]["FAIL"] else 0
    if args.cmd == "replay-vendor":
        result = replay_vendor_samples(args.contracts_dir)
        if args.json:
            pathlib.Path(args.json).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"problems": result["problems"],
                          "statuses": sorted({x["status"] for x in result["results"]})}), file=out)
        return 1 if any(x["status"] == "FAIL" for x in result["results"]) else 0
    a = json.loads(pathlib.Path(args.a).read_text(encoding="utf-8"))
    b = json.loads(pathlib.Path(args.b).read_text(encoding="utf-8"))
    diff = compare(a, b)
    print(json.dumps(diff, indent=2), file=out)
    return 1 if diff["regressions"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
