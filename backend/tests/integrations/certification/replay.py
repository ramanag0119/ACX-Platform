"""Controlled replay of OFFICIAL vendor samples (none exist yet).

Wraps the existing contract runner (`app.integrations.contracts`) with the extra
controls a real vendor sample needs:

* provenance in the manifest: vendor, product, protocol, protocol_version, source
  (document / message reference), received_on (ISO date), pii_status;
* the sample directory must not be a synthetic-fixture location;
* each sample file must exist and be <= MAX_SAMPLE_BYTES; files are hashed before and
  after the run and must be unchanged (replay never rewrites samples);
* pii_status "contains-guest-data" is refused unless HF-21 (retention / encryption) is
  Approved in the canonical register -- it is not, so such samples are BLOCKED;
* results never PASS unless the contract runner passed against the PRODUCTION adapters,
  which today are blocked (HF-06 / HF-07 / HF-11) -> every case is BLOCKED.

Reports carry case names, statuses and codes only -- never sample content.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from datetime import date
from typing import Any

from app.integrations.contracts import run_contracts
from app.integrations.domain.approvals import DECISIONS, DecisionStatus

MAX_SAMPLE_BYTES = 1024 * 1024
PII_STATUSES = {"synthetic-by-vendor", "anonymised", "contains-guest-data"}
PROVENANCE_KEYS = ("vendor", "product", "protocol", "protocol_version", "source", "received_on", "pii_status")
SYNTHETIC_DIRS = ("simulators", "certification")


def _hash_dir(folder: pathlib.Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()}


def validate_provenance(doc: dict[str, Any], folder: pathlib.Path) -> list[str]:
    problems = [f"missing provenance '{k}'" for k in PROVENANCE_KEYS if not doc.get(k)]
    if doc.get("pii_status") and doc["pii_status"] not in PII_STATUSES:
        problems.append("pii_status must be one of " + ", ".join(sorted(PII_STATUSES)))
    if doc.get("received_on"):
        try:
            date.fromisoformat(doc["received_on"])
        except ValueError:
            problems.append("received_on must be an ISO date")
    if any(part in SYNTHETIC_DIRS for part in folder.resolve().parts):
        problems.append("vendor samples must not live in a synthetic-fixture directory")
    for case in doc.get("cases") or []:
        f = folder / str(case.get("file", ""))
        if f.is_file() and f.stat().st_size > MAX_SAMPLE_BYTES:
            problems.append(f"sample '{case['file']}' exceeds {MAX_SAMPLE_BYTES} bytes")
    return problems


def hf21_approved() -> bool:
    d = DECISIONS.get("HF-21")
    return bool(d and d.status is DecisionStatus.APPROVED and d.evidence)


def replay_vendor_samples(contracts_dir: str | pathlib.Path) -> dict[str, Any]:
    root = pathlib.Path(contracts_dir)
    out: dict[str, Any] = {"contracts_dir": str(root), "vendors": [], "results": [], "problems": []}
    manifests = sorted(root.glob("*/manifest.json")) if root.is_dir() else []
    if not manifests:
        out["problems"].append("no official vendor samples supplied (HF-07 / HF-11)")
        out["results"].append({"vendor": "-", "case": "official-samples", "status": "BLOCKED",
                               "detail": "no official vendor samples"})
        return out
    for manifest in manifests:
        folder = manifest.parent
        out["vendors"].append(folder.name)
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        problems = validate_provenance(doc, folder)
        if doc.get("pii_status") == "contains-guest-data" and not hf21_approved():
            problems.append("samples contain guest data and HF-21 (retention/encryption) is not approved")
        if problems:
            out["results"].extend({"vendor": folder.name, "case": "manifest", "status": "BLOCKED", "detail": p}
                                  for p in problems)
            continue
        before = _hash_dir(folder)
        report = run_contracts(folder.parent)
        if _hash_dir(folder) != before:  # pragma: no cover - the runner only reads
            out["problems"].append(f"{folder.name}: sample files changed during replay")
        for r in report.results:
            if r.vendor != folder.name:
                continue
            status = "PASS" if r.status == "passed" else "FAIL" if r.status == "failed" else "BLOCKED"
            out["results"].append({"vendor": r.vendor, "case": r.case, "status": status, "detail": r.detail})
    return out
