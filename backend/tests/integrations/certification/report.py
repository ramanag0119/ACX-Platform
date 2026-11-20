"""Certification reports (JSON + Markdown) and run comparison."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from .core import Result, Status, new_run_id

DISCLAIMER = ("Synthetic certification evidence. It validates engineering behaviour only and is NOT "
              "vendor certification. Official vendor contract scenarios are BLOCKED until vendor "
              "documents and samples are received (HF-06, HF-07, HF-08, HF-11).")


def build_report(results: list[Result], *, run_id: str | None = None, label: str = "") -> dict[str, Any]:
    counts = Counter(str(r.status) for r in results)
    return {
        "run_id": run_id or new_run_id(),
        "label": label,
        "generated_at": datetime.now(UTC).isoformat(),
        "disclaimer": DISCLAIMER,
        "counts": {s.value: counts.get(s.value, 0) for s in Status},
        "results": [{**asdict(r), "status": str(r.status)} for r in results],
    }


def to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)


def to_markdown(report: dict[str, Any]) -> str:
    c = report["counts"]
    lines = [
        f"# Integration certification run `{report['run_id']}`",
        "",
        f"> {report['disclaimer']}",
        "",
        f"Generated {report['generated_at']} · PASS {c['PASS']} · FAIL {c['FAIL']} · "
        f"BLOCKED {c['BLOCKED']} · NOT RUN {c['NOT RUN']}",
        "",
        "| Scenario | Protocol | Category | Status | Reason | Correlation |",
        "|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        reason = (r["reason"] or "").replace("|", "/")[:160]
        lines.append(f"| {r['scenario_id']} | {r['protocol']} | {r['category']} | **{r['status']}** | "
                     f"{reason} | {r['evidence'].get('correlation_id') or ''} |")
    return "\n".join(lines) + "\n"


def compare(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Status changes from run `a` to run `b` (regressions = was PASS, now not)."""
    sa = {r["scenario_id"]: r["status"] for r in a["results"]}
    sb = {r["scenario_id"]: r["status"] for r in b["results"]}
    changed = {k: {"from": sa.get(k), "to": sb.get(k)} for k in sorted(set(sa) | set(sb)) if sa.get(k) != sb.get(k)}
    return {
        "from_run": a["run_id"], "to_run": b["run_id"],
        "regressions": sorted(k for k, v in changed.items() if v["from"] == "PASS"),
        "improvements": sorted(k for k, v in changed.items() if v["to"] == "PASS"),
        "added": sorted(set(sb) - set(sa)), "removed": sorted(set(sa) - set(sb)),
        "changed": changed,
    }
