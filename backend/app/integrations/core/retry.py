"""Bounded retry policy.

Only TRANSIENT errors are retried. Everything else -- validation, protocol,
security, conflicts, unsupported types, missing vendor specs, missing
approvals -- is dead-lettered on the first failure, so a bad message can never
loop. Back-off is exponential and capped; jitter is optional and injected so
tests stay deterministic. Per-message-type policies are pending HF-27.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.integrations.core.errors import IntegrationError


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    next_attempt_at: datetime | None
    reason: str


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: float = 5.0
    max_delay_seconds: float = 900.0
    multiplier: float = 2.0
    #: Maps a delay to a jittered delay. Identity by default (deterministic).
    jitter: Callable[[float], float] | None = None

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay_seconds <= 0 or self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("delays must be positive and max >= base")
        if self.multiplier < 1:
            raise ValueError("multiplier must be >= 1")

    def delay_for(self, attempt: int) -> float:
        """Delay after the `attempt`-th failed attempt (1-based)."""
        if attempt < 1:
            raise ValueError("attempt is 1-based")
        raw = self.base_delay_seconds * (self.multiplier ** (attempt - 1))
        delay = min(self.max_delay_seconds, raw)
        if self.jitter is not None:
            delay = max(0.0, min(self.max_delay_seconds, self.jitter(delay)))
        return delay

    def decide(self, error: IntegrationError, *, attempts_made: int, now: datetime) -> RetryDecision:
        if not error.retryable:
            return RetryDecision(False, None, f"non_retryable:{error.category}")
        if attempts_made >= self.max_attempts:
            return RetryDecision(False, None, "max_attempts_exhausted")
        return RetryDecision(
            True, now + timedelta(seconds=self.delay_for(attempts_made)), "transient"
        )


def full_jitter(delay: float) -> float:
    """Optional production jitter (AWS 'full jitter')."""
    return random.uniform(0, delay)  # noqa: S311 - not security sensitive
