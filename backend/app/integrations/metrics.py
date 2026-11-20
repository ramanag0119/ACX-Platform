"""In-process integration counters.

Deliberately dependency-free (no Prometheus client is approved). Exposed by
GET /integrations/metrics. Labels are low-cardinality identifiers only --
never payload values, client secrets or guest data.
"""

from __future__ import annotations

import threading
from collections import Counter
from datetime import datetime


class IntegrationMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Counter[str] = Counter()
        self._gauges: dict[str, float] = {}
        self._last_seen: dict[str, datetime] = {}

    def inc(self, name: str, amount: int = 1, **labels: str) -> None:
        key = name + "".join(f"|{k}={labels[k]}" for k in sorted(labels))
        with self._lock:
            self._counters[key] += amount

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def heartbeat(self, component: str, when: datetime) -> None:
        with self._lock:
            self._last_seen[component] = when

    def last_heartbeat(self, component: str) -> datetime | None:
        with self._lock:
            return self._last_seen.get(component)

    def get(self, name: str, **labels: str) -> int:
        key = name + "".join(f"|{k}={labels[k]}" for k in sorted(labels))
        with self._lock:
            return self._counters.get(key, 0)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "counters": dict(sorted(self._counters.items())),
                "gauges": dict(sorted(self._gauges.items())),
                "heartbeats": {k: v.isoformat() for k, v in sorted(self._last_seen.items())},
            }
