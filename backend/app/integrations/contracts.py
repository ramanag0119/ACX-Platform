"""Vendor contract-test harness (library + CLI).

Loads vendor-supplied sample messages described by a manifest and runs them
against an adapter factory -- by default the PRODUCTION adapters, which refuse
everything until a verified FIAS spec / HTNG profile is registered. Produces a
machine-readable report. It never fabricates expectations: anything the
manifest or the approved specification does not define is reported as
`blocked` or `missing`, not as passed.

    python -m app.integrations.contracts <contracts_dir> [--report report.json]

Directory layout: <contracts_dir>/<vendor>/manifest.json + sample files.

manifest.json
    vendor, product, protocol ("fias" | "htng"), protocol_version,
    specification   document title / version / section (required),
    profile         HTNG profile id + version (htng only, optional),
    cases: [{name, file, direction: "inbound"|"outbound",
             expect: {message_type, property_code, idempotency_key,
                      body_subset, error_code,
                      ack: {outcome}}}]          # ack: HTNG profiles only
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from app.integrations.adapters.base import AdapterReadiness, BaseProtocolAdapter, TransportContext
from app.integrations.core.errors import IntegrationError

REQUIRED_KEYS = ("vendor", "product", "protocol", "specification", "cases")
PROTOCOLS = ("fias", "htng")


@dataclass
class CaseResult:
    vendor: str
    case: str
    status: str  # passed | failed | blocked | missing | invalid
    detail: str = ""


@dataclass
class ContractReport:
    contracts_dir: str
    vendors: list[str] = field(default_factory=list)
    results: list[CaseResult] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.results:
            out[r.status] = out.get(r.status, 0) + 1
        return out

    @property
    def ok(self) -> bool:
        return bool(self.results) and not self.problems and all(r.status == "passed" for r in self.results)

    def to_dict(self) -> dict[str, Any]:
        return {"contracts_dir": self.contracts_dir, "vendors": self.vendors, "counts": self.counts(),
                "ok": self.ok, "problems": self.problems, "results": [asdict(r) for r in self.results]}


def production_adapter(protocol: str, manifest: dict) -> BaseProtocolAdapter:
    from app.integrations.adapters.fias.adapter import FIASAdapter
    from app.integrations.adapters.htng.adapter import HTNGAdapter
    from app.integrations.adapters.htng.schema import SchemaRegistry

    if protocol == "fias":
        return FIASAdapter()
    profile = manifest.get("profile") or {}
    return HTNGAdapter(SchemaRegistry(), profile_id=profile.get("id"), version=profile.get("version"))


AdapterFactory = Callable[[str, dict], BaseProtocolAdapter]


def validate_manifest(doc: Any, folder: pathlib.Path) -> list[str]:
    if not isinstance(doc, dict):
        return ["manifest is not a JSON object"]
    problems = [f"missing key '{k}'" for k in REQUIRED_KEYS if k not in doc]
    if doc.get("protocol") not in PROTOCOLS:
        problems.append("protocol must be 'fias' or 'htng'")
    for i, case in enumerate(doc.get("cases") or []):
        name = case.get("name") or f"#{i}"
        if not case.get("file"):
            problems.append(f"case {name}: no sample file")
        elif not (folder / case["file"]).is_file():
            problems.append(f"case {name}: sample file '{case['file']}' not found")
        if case.get("direction", "inbound") not in ("inbound", "outbound"):
            problems.append(f"case {name}: direction must be inbound/outbound")
        if not isinstance(case.get("expect"), dict) or not case["expect"]:
            problems.append(f"case {name}: no expectations (a sample without expectations proves nothing)")
    if not doc.get("cases"):
        problems.append("no cases")
    return problems


def _run_case(adapter: BaseProtocolAdapter, protocol: str, folder: pathlib.Path, case: dict) -> tuple[str, str]:
    expect = case["expect"]
    if case.get("direction", "inbound") == "outbound":
        return "blocked", "outbound contract cases need a verified serializer mapping (not executed)"
    raw = (folder / case["file"]).read_bytes()
    ctx = TransportContext(transport="contract-test", bound_property_code=expect.get("bound_property_code"))
    try:
        decoded = adapter.decode(raw, ctx)
    except IntegrationError as exc:
        if expect.get("error_code") == exc.code:
            return "passed", f"rejected as expected ({exc.code})"
        if exc.category.value == "vendor_blocked":
            return "blocked", f"{exc.code}: {exc.detail.get('decision', '')}"
        return "failed", f"unexpected error {exc.code}"
    if "error_code" in expect:
        return "failed", f"expected error {expect['error_code']}, message was accepted"
    mismatches = []
    if "message_type" in expect and decoded.message_type != expect["message_type"]:
        mismatches.append("message_type")
    for key in ("property_code", "idempotency_key"):
        if key in expect and getattr(decoded, key) != expect[key]:
            mismatches.append(key)
    for key, value in (expect.get("body_subset") or {}).items():
        if decoded.body.get(key) != value:
            mismatches.append(f"body.{key}")
    if mismatches:
        return "failed", "mismatch: " + ", ".join(mismatches)
    if "ack" in expect:
        if protocol != "htng":
            return "blocked", "acknowledgement rules are not specified (HF-06)"
        from app.integrations.transport.soap import parse_soap
        from app.integrations.transport.xml_security import qname

        root = parse_soap(raw).body
        ack = adapter.build_response(qname(root), expect["ack"].get("outcome", "accepted"), "contract-test")
        if ack is None:
            return "failed", "profile defines no acknowledgement"
    return "passed", ""


def run_contracts(contracts_dir: str | pathlib.Path, *, adapter_factory: AdapterFactory = production_adapter) -> ContractReport:
    root = pathlib.Path(contracts_dir)
    report = ContractReport(contracts_dir=str(root))
    manifests = sorted(root.glob("*/manifest.json")) if root.is_dir() else []
    if not manifests:
        report.problems.append("no vendor manifests: official samples not supplied (HF-07 / HF-11)")
        return report
    for path in manifests:
        folder = path.parent
        report.vendors.append(folder.name)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            report.results.append(CaseResult(folder.name, "manifest", "invalid", "manifest is not valid JSON"))
            continue
        problems = validate_manifest(doc, folder)
        if problems:
            report.results.extend(CaseResult(folder.name, "manifest", "invalid", p) for p in problems)
            continue
        adapter = adapter_factory(doc["protocol"], doc)
        if adapter.status().readiness is AdapterReadiness.BLOCKED:
            note = "adapter BLOCKED: " + ", ".join(adapter.status().blocking_decisions)
        else:
            note = ""
        for case in doc["cases"]:
            status, detail = _run_case(adapter, doc["protocol"], folder, case)
            report.results.append(CaseResult(folder.name, case["name"], status, detail or note))
    return report


def to_markdown(report: ContractReport) -> str:
    lines = [f"# Vendor contract report — {report.contracts_dir}", "", f"Counts: {report.counts()}", ""]
    lines += [f"- PROBLEM: {p}" for p in report.problems]
    lines += ["", "| Vendor | Case | Status | Detail |", "|---|---|---|---|"]
    lines += [f"| {r.vendor} | {r.case} | {r.status} | {r.detail} |" for r in report.results]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="app.integrations.contracts")
    p.add_argument("contracts_dir")
    p.add_argument("--report", help="write JSON report here (a .md path writes Markdown)")
    args = p.parse_args(argv)
    report = run_contracts(args.contracts_dir)
    if args.report:
        out = pathlib.Path(args.report)
        out.write_text(to_markdown(report) if out.suffix == ".md" else json.dumps(report.to_dict(), indent=2),
                       encoding="utf-8")
    print(json.dumps({"counts": report.counts(), "ok": report.ok, "problems": report.problems}))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
