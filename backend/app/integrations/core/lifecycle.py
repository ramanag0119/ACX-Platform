"""Message lifecycle: the only legal status transitions.

    RECEIVED -> VALIDATED -> PENDING -> PROCESSING -> SUCCEEDED
        |           |                     |   ^
        v           v                     |   |  (lease expired: re-claimed
     REJECTED    REJECTED                 |   |   by another worker)
                                          +---+
                                          |
                                          +--> RETRY_WAIT --> PROCESSING
                                          |
                                          +--> DEAD_LETTER --(redrive)--> PENDING

SUCCEEDED and REJECTED are terminal. DEAD_LETTER leaves only through an
authorised, audited redrive.
"""

from __future__ import annotations

from app.integrations.core.envelope import MessageStatus as S
from app.integrations.core.errors import InvalidTransition

ALLOWED: dict[S, frozenset[S]] = {
    S.RECEIVED: frozenset({S.VALIDATED, S.REJECTED}),
    S.VALIDATED: frozenset({S.PENDING, S.REJECTED}),
    S.PENDING: frozenset({S.PROCESSING}),
    S.PROCESSING: frozenset({S.PROCESSING, S.SUCCEEDED, S.RETRY_WAIT, S.DEAD_LETTER}),
    S.RETRY_WAIT: frozenset({S.PROCESSING}),
    S.DEAD_LETTER: frozenset({S.PENDING}),
    S.SUCCEEDED: frozenset(),
    S.REJECTED: frozenset(),
}

TERMINAL: frozenset[S] = frozenset({S.SUCCEEDED, S.REJECTED})

#: Statuses a worker may claim (PROCESSING only once its lease has expired).
CLAIMABLE: frozenset[S] = frozenset({S.PENDING, S.RETRY_WAIT, S.PROCESSING})


def can_transition(current: S, target: S) -> bool:
    return target in ALLOWED[current]


def assert_transition(current: S | str, target: S | str) -> None:
    current, target = S(current), S(target)
    if not can_transition(current, target):
        raise InvalidTransition(
            f"Status transition {current} -> {target} is not allowed.",
            detail={"from": str(current), "to": str(target)},
        )
