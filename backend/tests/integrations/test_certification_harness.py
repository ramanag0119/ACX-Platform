"""Certification harness: registry, engine, evidence, reports, replay safety, CLI,
and every registered scenario executed through the engine."""

from __future__ import annotations

import io
import json
import pathlib

import pytest

from .certification import core
from .certification.__main__ import main as cli
from .certification.core import Category, HarnessEnv, Scenario, Status, load_all
from .certification.replay import MAX_SAMPLE_BYTES, replay_vendor_samples
from .certification.report import build_report, compare, to_json, to_markdown

SCENARIOS = load_all()


@pytest.fixture(scope="module")
def harness_env():
    env = HarnessEnv.from_environment()
    yield env
    env.close()


# --- every scenario, through the engine ------------------------------------------------
@pytest.mark.parametrize("scenario_id", sorted(SCENARIOS))
def test_scenario(scenario_id, harness_env):
    result = core._run_one(SCENARIOS[scenario_id], harness_env)  # noqa: SLF001
    if result.status is Status.NOT_RUN:
        pytest.skip(result.reason)
    if SCENARIOS[scenario_id].category is Category.VENDOR:
        assert result.status is Status.BLOCKED, result.reason
        return
    assert result.status is Status.PASS, f"{result.status}: {result.reason}"


# --- registry ------------------------------------------------------------------------
def test_registry_is_complete_deterministic_and_categorised():
    ids = list(SCENARIOS)
    assert len(ids) == 45 and ids == sorted(ids)
    by_proto = {p: sum(1 for s in SCENARIOS.values() if s.protocol == p) for p in ("htng", "fias", "hms")}
    assert by_proto == {"htng": 17, "fias": 18, "hms": 10}
    vendor = [s for s in SCENARIOS.values() if s.category is Category.VENDOR]
    assert {s.id for s in vendor} == {"HTNG-OFF-001", "HTNG-OFF-002", "FIAS-OFF-001", "FIAS-OFF-002", "FIAS-OFF-003"}
    assert all("vendor" in s.requires and s.blocked_by for s in vendor)
    assert all(s.requires == {"hms_db"} for s in SCENARIOS.values() if s.protocol == "hms")


@pytest.mark.parametrize("bad_id", ["HTNG-1", "XYZ-SYN-001", "FIAS-SYN-01"])
def test_scenario_ids_are_validated(bad_id):
    with pytest.raises(ValueError):
        Scenario(bad_id, "fias", Category.ENGINE, "x", {}, (), lambda ctx: None)


def test_vendor_scenarios_must_name_blockers():
    with pytest.raises(ValueError):
        Scenario("FIAS-OFF-099", "fias", Category.VENDOR, "x", {}, (), lambda ctx: None)


# --- engine rules --------------------------------------------------------------------
def _sc(fn, *, category=Category.ENGINE, requires=(), blocked_by=()):
    return Scenario("FIAS-SYN-999", "fias", category, "adhoc", {}, (), fn, frozenset(requires), blocked_by)


def test_engine_records_failures_and_errors():
    def failing(ctx):
        ctx.expect(False, "expected failure")

    def crashing(ctx):
        raise KeyError("boom")

    env = HarnessEnv()
    assert core._run_one(_sc(failing), env).status is Status.FAIL  # noqa: SLF001
    r = core._run_one(_sc(crashing), env)  # noqa: SLF001
    assert r.status is Status.FAIL and "KeyError" in r.reason


def test_vendor_scenario_can_never_pass():
    sc = _sc(lambda ctx: None, category=Category.VENDOR, blocked_by=("HF-11",))
    assert core._run_one(sc, HarnessEnv()).status is Status.BLOCKED  # noqa: SLF001


def test_missing_environment_is_not_run_not_pass():
    r = core._run_one(_sc(lambda ctx: None, requires=("hms_db",)), HarnessEnv())  # noqa: SLF001
    assert r.status is Status.NOT_RUN and "hms_db" in r.reason


def test_scenario_can_declare_itself_blocked():
    def blocked(ctx):
        raise core.Blocked("needs HF-06")

    assert core._run_one(_sc(blocked), HarnessEnv()).status is Status.BLOCKED  # noqa: SLF001


# --- evidence ------------------------------------------------------------------------
def test_evidence_masks_pii_and_refuses_secrets():
    ev = core.Evidence(observations=["guest jane@example.com card 4111111111111111"], response={"guest_name": "Jane"})
    data = ev.redacted([])
    assert "jane@example.com" not in json.dumps(data) and data["response"]["guest_name"] == "***"
    with pytest.raises(ValueError):
        core.Evidence(observations=["leaked-secret-value-xyz"]).redacted(["leaked-secret-value-xyz"])


# --- reports ---------------------------------------------------------------------------
def _result(sid, status):
    return core.Result(sid, "fias", str(Category.ENGINE), "d", status, "", "t", 1.0, {})


def test_reports_render_and_compare():
    a = build_report([_result("FIAS-SYN-001", Status.PASS), _result("FIAS-SYN-002", Status.FAIL)], run_id="a")
    b = build_report([_result("FIAS-SYN-001", Status.FAIL), _result("FIAS-SYN-002", Status.PASS),
                      _result("FIAS-SYN-003", Status.PASS)], run_id="b")
    assert json.loads(to_json(a))["counts"] == {"PASS": 1, "FAIL": 1, "BLOCKED": 0, "NOT RUN": 0}
    md = to_markdown(b)
    assert "NOT vendor certification" in md and "| FIAS-SYN-001 | fias |" in md
    diff = compare(a, b)
    assert diff["regressions"] == ["FIAS-SYN-001"] and diff["improvements"] == ["FIAS-SYN-002", "FIAS-SYN-003"]
    assert diff["added"] == ["FIAS-SYN-003"]


# --- vendor sample replay safety ---------------------------------------------------------
def _manifest(folder: pathlib.Path, **over):
    doc = {"vendor": "V", "product": "P", "protocol": "fias", "protocol_version": "1", "specification": "doc §1",
           "source": "email ref 1", "received_on": "2026-11-20", "pii_status": "anonymised",
           "cases": [{"name": "c1", "file": "s.bin", "expect": {"message_type": "a.b"}}]}
    doc.update(over)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text(json.dumps(doc), encoding="utf-8")
    (folder / "s.bin").write_bytes(b"VENDOR-SAMPLE-BYTES")
    return doc


def test_replay_without_samples_is_blocked(tmp_path):
    r = replay_vendor_samples(tmp_path / "none")
    assert [x["status"] for x in r["results"]] == ["BLOCKED"] and r["problems"]


def test_replay_with_valid_provenance_is_blocked_by_production_adapters_and_never_rewrites(tmp_path):
    _manifest(tmp_path / "v1")
    before = (tmp_path / "v1" / "s.bin").read_bytes()
    r = replay_vendor_samples(tmp_path)
    assert {x["status"] for x in r["results"]} == {"BLOCKED"}
    assert (tmp_path / "v1" / "s.bin").read_bytes() == before
    assert "VENDOR-SAMPLE-BYTES" not in json.dumps(r)


@pytest.mark.parametrize("override,fragment", [
    ({"source": ""}, "missing provenance 'source'"),
    ({"received_on": "yesterday"}, "ISO date"),
    ({"pii_status": "unknown"}, "pii_status must be"),
    ({"pii_status": "contains-guest-data"}, "HF-21"),
])
def test_replay_refuses_incomplete_or_unapproved_samples(tmp_path, override, fragment):
    _manifest(tmp_path / "v1", **override)
    r = replay_vendor_samples(tmp_path)
    assert all(x["status"] == "BLOCKED" for x in r["results"])
    assert any(fragment in x["detail"] for x in r["results"])


def test_replay_refuses_oversized_samples(tmp_path):
    _manifest(tmp_path / "v1")
    (tmp_path / "v1" / "s.bin").write_bytes(b"x" * (MAX_SAMPLE_BYTES + 1))
    r = replay_vendor_samples(tmp_path)
    assert any("exceeds" in x["detail"] for x in r["results"])


def test_replay_refuses_synthetic_fixture_locations(tmp_path):
    _manifest(tmp_path / "certification" / "v1")
    r = replay_vendor_samples(tmp_path / "certification")
    assert any("synthetic-fixture" in x["detail"] for x in r["results"])


# --- CLI ------------------------------------------------------------------------------
def test_cli_list_run_and_compare(tmp_path):
    out = io.StringIO()
    assert cli(["list"], out=out) == 0 and len(out.getvalue().splitlines()) == 45
    j1, j2, md = tmp_path / "a.json", tmp_path / "b.json", tmp_path / "a.md"
    assert cli(["run", "--id", "FIAS-SYN-007", "--id", "FIAS-OFF-001", "--json", str(j1), "--md", str(md)],
               out=io.StringIO()) == 0
    report = json.loads(j1.read_text())
    assert {r["scenario_id"]: r["status"] for r in report["results"]} == {"FIAS-OFF-001": "BLOCKED", "FIAS-SYN-007": "PASS"}
    assert md.read_text().startswith("# Integration certification run")
    assert cli(["run", "--id", "FIAS-SYN-007", "--json", str(j2)], out=io.StringIO()) == 0
    out = io.StringIO()
    assert cli(["compare", str(j1), str(j2)], out=out) == 0
    assert json.loads(out.getvalue())["removed"] == ["FIAS-OFF-001"]
    assert cli(["run", "--id", "NOPE-SYN-001"], out=io.StringIO()) == 2
    assert cli(["replay-vendor", str(tmp_path / "none")], out=io.StringIO()) == 0
