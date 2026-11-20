"""Vendor contract harness.

1. `test_official_vendor_contracts` runs every manifest under
   tests/integrations/vendor_contracts/ against the PRODUCTION adapters. No
   official samples exist (HF-07 / HF-11), so it is an explicit SKIP.
2. The remaining tests exercise the HARNESS ITSELF on SYNTHETIC manifests built
   in a temp directory with the TEST adapters. They are not vendor evidence.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from app.integrations.adapters.fias.adapter import FIASAdapter
from app.integrations.adapters.htng.adapter import HTNGAdapter
from app.integrations.adapters.htng.schema import SchemaRegistry
from app.integrations.contracts import main, run_contracts, to_markdown, validate_manifest
from app.integrations.simulators.fixtures import (
    PROVISIONAL_TEST_FIAS_SPEC,
    PROVISIONAL_TEST_XML_PROFILE,
    generic_arrival_soap,
)

CONTRACTS = pathlib.Path(__file__).parent / "vendor_contracts"


def test_official_vendor_contracts():
    report = run_contracts(CONTRACTS)
    if not report.vendors:
        pytest.skip("No official vendor samples supplied (HF-07 HTNG WSDL/XSD, HF-11 FIAS manual). "
                    "Add tests/integrations/vendor_contracts/<vendor>/manifest.json.")
    assert report.ok, json.dumps(report.to_dict(), indent=2)


# --- harness self-tests (SYNTHETIC, TEST adapters) ------------------------------------
def synthetic_adapter_factory(protocol, manifest):
    if protocol == "fias":
        return FIASAdapter(PROVISIONAL_TEST_FIAS_SPEC, allow_unverified=True, app_env="test")
    reg = SchemaRegistry(allow_unverified=True, app_env="test")
    reg.register(PROVISIONAL_TEST_XML_PROFILE)
    return HTNGAdapter(reg, profile_id="acx-generic-xml-test", version="0")




def write(folder: pathlib.Path, manifest: dict, files: dict[str, bytes]):
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name, data in files.items():
        (folder / name).write_bytes(data)


def synthetic(tmp_path):
    write(tmp_path / "synthetic-fias", {
        "vendor": "SYNTHETIC", "product": "none", "protocol": "fias", "specification": "TEST fixture",
        "cases": [
            {"name": "arrival", "file": "a.bin", "expect": {
                "message_type": "test.guest_arrival", "property_code": "HOTEL-A",
                "idempotency_key": "ZA:m-1", "body_subset": {"room": "101"}}},
            {"name": "unknown-record", "file": "bad.bin", "expect": {"error_code": "unsupported_message"}},
            {"name": "ack", "file": "a.bin", "expect": {"message_type": "test.guest_arrival", "ack": {}}},
            {"name": "wrong-room", "file": "a.bin", "expect": {"body_subset": {"room": "999"}}},
        ]}, {"a.bin": b"ZA|MIm-1|PCHOTEL-A|RN101|SRs-1|", "bad.bin": b"QQ|X|"})
    write(tmp_path / "synthetic-xml", {
        "vendor": "SYNTHETIC", "product": "none", "protocol": "htng", "specification": "TEST fixture",
        "profile": {"id": "acx-generic-xml-test", "version": "0"},
        "cases": [{"name": "arrival-ack", "file": "r.xml", "expect": {
            "message_type": "test.guest_arrival", "idempotency_key": "r1", "ack": {"outcome": "accepted"}}}],
    }, {"r.xml": generic_arrival_soap(message_ref="r1", property_code="H", room="1", stay_ref="s")})
    return tmp_path


def test_harness_reports_pass_fail_blocked(tmp_path):
    report = run_contracts(synthetic(tmp_path), adapter_factory=synthetic_adapter_factory)
    by = {(r.vendor, r.case): r for r in report.results}
    assert by[("synthetic-fias", "arrival")].status == "passed"
    assert by[("synthetic-fias", "unknown-record")].status == "passed"
    assert by[("synthetic-fias", "ack")].status == "blocked" and "HF-06" in by[("synthetic-fias", "ack")].detail
    assert by[("synthetic-fias", "wrong-room")].status == "failed"
    assert by[("synthetic-xml", "arrival-ack")].status == "passed"
    assert report.counts() == {"passed": 3, "blocked": 1, "failed": 1} and not report.ok
    md = to_markdown(report)
    assert "| synthetic-fias | wrong-room | failed |" in md


def test_production_adapters_report_blocked_not_passed(tmp_path):
    report = run_contracts(synthetic(tmp_path))  # default = production adapters
    assert {r.status for r in report.results} == {"blocked"}
    assert all("HF-11" in r.detail or "HF-07" in r.detail for r in report.results)


def test_missing_and_invalid_manifests_are_reported(tmp_path):
    empty = run_contracts(tmp_path / "nothing-here")
    assert empty.problems and not empty.ok
    write(tmp_path / "v1", {"vendor": "x", "protocol": "smtp", "cases": [{"name": "c", "file": "nope.bin"}]}, {})
    report = run_contracts(tmp_path)
    details = " ".join(r.detail for r in report.results)
    assert all(r.status == "invalid" for r in report.results)
    for fragment in ("missing key 'product'", "missing key 'specification'", "protocol must be",
                     "not found", "no expectations"):
        assert fragment in details
    assert validate_manifest([], tmp_path) == ["manifest is not a JSON object"]


def test_cli_writes_json_and_markdown_reports(tmp_path, capsys):
    out_json = tmp_path / "r.json"
    out_md = tmp_path / "r.md"
    assert main([str(tmp_path / "none"), "--report", str(out_json)]) == 1
    assert json.loads(out_json.read_text())["ok"] is False
    assert main([str(tmp_path / "none"), "--report", str(out_md)]) == 1
    assert out_md.read_text().startswith("# Vendor contract report")
    assert '"ok": false' in capsys.readouterr().out
