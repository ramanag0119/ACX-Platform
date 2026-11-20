"""Scenario registry, execution engine and evidence collector."""

from __future__ import annotations

import os
import re
import time
import traceback
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.integrations.core.masking import mask_mapping


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT RUN"


class Category(StrEnum):
    TRANSPORT = "generic transport validation"
    ENGINE = "shared-engine validation"
    HMS = "HMS workflow validation"
    VENDOR = "official vendor contract validation"


ID_PATTERN = re.compile(r"^(HTNG|FIAS|HMS)-(SYN|OFF)-\d{3}$")


class Blocked(Exception):
    """Raised by a scenario that cannot run without an external dependency."""


@dataclass
class Evidence:
    """Identifiers and outcomes only. Never payload values, guest data or secrets."""

    correlation_id: str | None = None
    adapter: str | None = None
    input_ref: str | None = None
    processing_result: str | None = None
    failure_category: str | None = None
    failure_code: str | None = None
    response: dict[str, Any] = field(default_factory=dict)
    hms_before: dict[str, Any] = field(default_factory=dict)
    hms_after: dict[str, Any] = field(default_factory=dict)
    audit_actions: list[str] = field(default_factory=list)
    retry_dlq: dict[str, Any] = field(default_factory=dict)
    #: free text, still scrubbed for e-mails / long digit runs. (A field named
    #: "notes" would be masked wholesale by key name.)
    observations: list[str] = field(default_factory=list)

    def redacted(self, secrets: list[str]) -> dict[str, Any]:
        raw = repr(asdict(self))  # check BEFORE masking: masking could hide a leak
        for s in secrets:
            if s and s in raw:
                raise ValueError("evidence would contain a secret; refusing to record it")
        return mask_mapping(asdict(self))


@dataclass
class Scenario:
    id: str
    protocol: str  # "htng" | "fias" | "hms"
    category: Category
    description: str
    expected: dict[str, Any]
    evidence_required: tuple[str, ...]
    run: Callable[["Context"], None]
    requires: frozenset[str] = frozenset()  # "mysql", "hms_db", "vendor"
    blocked_by: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not ID_PATTERN.match(self.id):
            raise ValueError(f"scenario id {self.id!r} must match {ID_PATTERN.pattern}")
        if self.category is Category.VENDOR and not self.blocked_by:
            raise ValueError("official vendor scenarios must name their blocking decisions")


@dataclass
class Result:
    scenario_id: str
    protocol: str
    category: str
    description: str
    status: Status
    reason: str
    started_at: str
    duration_ms: float
    evidence: dict[str, Any]


REGISTRY: dict[str, Scenario] = {}


def scenario(id: str, protocol: str, category: Category, description: str, *, expected: dict,
             evidence: tuple[str, ...] = (), requires: tuple[str, ...] = (), blocked_by: tuple[str, ...] = ()):
    def deco(fn: Callable[["Context"], None]) -> Callable[["Context"], None]:
        if id in REGISTRY:
            raise ValueError(f"duplicate scenario id {id}")
        REGISTRY[id] = Scenario(id, protocol, category, description, expected, tuple(evidence), fn,
                                frozenset(requires), tuple(blocked_by))
        return fn
    return deco


def load_all() -> dict[str, Scenario]:
    from . import scenarios_fias, scenarios_hms, scenarios_htng  # noqa: F401 - registration side effect

    return dict(sorted(REGISTRY.items()))


@dataclass
class HarnessEnv:
    mysql_url: str | None = None
    hms_db_url: str | None = None
    _hms_engine: Any = None
    _hms_gen: Any = None

    @classmethod
    def from_environment(cls) -> "HarnessEnv":
        return cls(os.environ.get("INTEGRATION_TEST_MYSQL_URL"), os.environ.get("INTEGRATION_TEST_HMS_DB_URL"))

    def available(self) -> set[str]:
        out = set()
        if self.mysql_url:
            out.add("mysql")
        if self.hms_db_url:
            out.add("hms_db")
        return out

    def hms_engine(self):
        """Seeded HMS schema on the DISPOSABLE database (built once per run)."""
        if self._hms_engine is None:
            from ..test_hms_domain_mysql import hms_engine_impl

            self._hms_gen = hms_engine_impl()
            self._hms_engine = next(self._hms_gen)
        return self._hms_engine

    def close(self) -> None:
        if self._hms_gen is not None:
            try:
                next(self._hms_gen)
            except StopIteration:
                pass
            self._hms_gen = self._hms_engine = None


class Context:
    def __init__(self, env: HarnessEnv) -> None:
        self.env = env
        self.evidence = Evidence()
        self.secrets: list[str] = []

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(message)


def run_scenarios(ids: list[str] | None = None, env: HarnessEnv | None = None) -> list[Result]:
    scenarios = load_all()
    env = env or HarnessEnv.from_environment()
    selected = [scenarios[i] for i in (ids or list(scenarios))]
    results: list[Result] = []
    try:
        for sc in selected:
            results.append(_run_one(sc, env))
    finally:
        env.close()
    return results


def _run_one(sc: Scenario, env: HarnessEnv) -> Result:
    started = datetime.now(UTC).isoformat()
    t0 = time.perf_counter()
    ctx = Context(env)
    if "vendor" in sc.requires:
        status, reason = Status.BLOCKED, "requires official vendor material: " + ", ".join(sc.blocked_by)
    elif missing := (sc.requires - env.available()):
        status, reason = Status.NOT_RUN, "disposable environment not configured: " + ", ".join(sorted(missing))
    else:
        try:
            sc.run(ctx)
            status, reason = Status.PASS, ""
        except Blocked as exc:
            status, reason = Status.BLOCKED, str(exc)
        except AssertionError as exc:
            status, reason = Status.FAIL, str(exc) or "assertion failed"
        except Exception as exc:  # noqa: BLE001 - recorded as a failure, never hidden
            status = Status.FAIL
            reason = f"{type(exc).__name__}: {exc}"[:500]
            ctx.evidence.observations.append(traceback.format_exc(limit=3)[-800:])
    if sc.category is Category.VENDOR and status is Status.PASS:  # defence in depth
        status, reason = Status.BLOCKED, "official contract scenarios cannot pass without vendor material"
    return Result(sc.id, sc.protocol, str(sc.category), sc.description, status, reason, started,
                  round((time.perf_counter() - t0) * 1000, 1), ctx.evidence.redacted(ctx.secrets))


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
