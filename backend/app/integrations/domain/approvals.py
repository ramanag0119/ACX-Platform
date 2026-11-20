"""Code-level mirror of the approval register (docs/HTNG_FIAS_DECISION_REGISTER.md).

Live HMS domain writes need BOTH:
  1. INTEGRATION_LIVE_DOMAIN_WRITES=true in the environment, AND
  2. every decision in REQUIRED_FOR_LIVE_WRITES recorded here as APPROVED,
     with the approval evidence reference.

(2) is deliberately a code change: approving a decision means a reviewed
commit that cites the evidence, not a flag someone can flip on a server.
Nothing below is approved -- no approval evidence exists in the repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.integrations.core.errors import ApprovalRequired


class DecisionStatus(StrEnum):
    OPEN = "Open"
    AWAITING_BUSINESS = "Awaiting Business Approval"
    AWAITING_VENDOR = "Awaiting Vendor Confirmation"
    AWAITING_DBA = "Awaiting DBA Approval"
    APPROVED = "Approved"


@dataclass(frozen=True)
class Decision:
    decision_id: str
    subject: str
    status: DecisionStatus
    evidence: str | None = None


DECISIONS: dict[str, Decision] = {
    d.decision_id: d
    for d in (
        Decision("HF-01", "PMS / HMS system-of-record ownership (operating model)", DecisionStatus.AWAITING_BUSINESS),
        Decision("HF-02", "External facility/property mapping ownership (entity ownership)", DecisionStatus.AWAITING_BUSINESS),
        Decision("HF-05", "FIAS external property-code case sensitivity", DecisionStatus.AWAITING_VENDOR),
        Decision("HF-07", "HTNG version / profile / schema scope", DecisionStatus.AWAITING_VENDOR),
        Decision("HF-06", "FIAS connection / link rules (framing, ACK, heartbeat, listening side)", DecisionStatus.AWAITING_VENDOR),
        Decision("HF-11", "FIAS official specification content (manual, record set, field definitions)", DecisionStatus.AWAITING_VENDOR),
        Decision("HF-18", "Integration principal / HMS actor for writes", DecisionStatus.OPEN),
        Decision("HF-19", "Facility authorization / isolation rules", DecisionStatus.AWAITING_BUSINESS),
        Decision("HF-21", "Raw-payload retention and encryption", DecisionStatus.OPEN),
        Decision("HF-39", "DBA / schema authorization for integration tables", DecisionStatus.AWAITING_DBA),
    )
}

REQUIRED_FOR_LIVE_WRITES: tuple[str, ...] = ("HF-01", "HF-02", "HF-05", "HF-19")


def pending(decision_ids: tuple[str, ...] | list[str], register: dict[str, Decision] | None = None) -> list[str]:
    register = DECISIONS if register is None else register
    out = []
    for did in decision_ids:
        d = register.get(did)
        if d is None or d.status is not DecisionStatus.APPROVED or not d.evidence:
            out.append(did)
    return out


class LiveWriteGate:
    def __init__(
        self,
        *,
        enabled_flag: bool,
        register: dict[str, Decision] | None = None,
        required: tuple[str, ...] = REQUIRED_FOR_LIVE_WRITES,
    ) -> None:
        self._enabled = enabled_flag
        self._register = DECISIONS if register is None else register
        self._required = required

    def blocking(self) -> list[str]:
        blockers = pending(self._required, self._register)
        if not self._enabled:
            blockers = ["INTEGRATION_LIVE_DOMAIN_WRITES", *blockers]
        return blockers

    def is_open(self) -> bool:
        return not self.blocking()

    def assert_open(self) -> None:
        blockers = self.blocking()
        if blockers:
            raise ApprovalRequired("Live HMS domain writes are not approved.", decisions=blockers)
