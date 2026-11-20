"""Long-running integration service: inbound worker + outbox relay + retention.

    INTEGRATION_ENABLED=true python -m app.integrations.service

Behaviour:
* Refuses to start unless INTEGRATION_ENABLED=true (exit code 3).
* Polls `InboundWorker.run_once()` and `OutboxRelay.run_once()`; sleeps
  `poll_interval` when idle, keeps going immediately while there is work.
* Any unexpected error (e.g. the database is down) is logged by type only,
  counted, and followed by a bounded exponential back-off. The loop never dies
  on a single failure; durable state means nothing is lost meanwhile.
* SIGTERM / SIGINT stop it gracefully: the current batch finishes, no new
  claims are taken. Messages a killed process held are re-claimed after their
  lease expires.
* Retention purge runs only when INTEGRATION_RETENTION_DAYS is set (HF-21).
* Several instances may run: claims are SKIP LOCKED and fenced. Hosting,
  restart policy and the single-owner rule for a FIAS link are HF-25/HF-26.

Outbound: the outbox relay runs only for protocols with a deliverable sender
(`build_outbound_senders`): an HTNG vendor endpoint configured AND an HTNG
adapter that is not BLOCKED. No vendor endpoint or link exists today, so no
relay runs; outbox rows wait (PENDING) instead of being dead-lettered.

FIAS link: started only when INTEGRATION_FIAS_LINK_ENABLED=true AND the link
can be built from approved contracts (transport/link_runtime.py); otherwise
the service refuses to start (exit code 4) and says which decision is missing.
"""

from __future__ import annotations

import logging
import signal
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.integrations.core.envelope import utcnow
from app.integrations.metrics import IntegrationMetrics
from app.integrations.processing.worker import InboundWorker, OutboxRelay, RunSummary

logger = logging.getLogger("hms.integrations.service")


@dataclass(frozen=True)
class ServiceSettings:
    poll_interval_seconds: float = 1.0
    batch_size: int = 10
    error_backoff_base_seconds: float = 1.0
    error_backoff_max_seconds: float = 60.0
    retention: timedelta | None = None
    purge_interval_seconds: float = 3600.0


class IntegrationService:
    def __init__(
        self,
        *,
        worker: InboundWorker,
        relay: OutboxRelay | None,
        settings: ServiceSettings,
        metrics: IntegrationMetrics,
        purge: Callable[[datetime], dict] | None = None,
        clock: Callable[[], datetime] = utcnow,
        stop_event: threading.Event | None = None,
    ) -> None:
        self._worker = worker
        self._relay = relay
        self._settings = settings
        self._metrics = metrics
        self._purge = purge if settings.retention is not None else None
        self._clock = clock
        self.stop_event = stop_event or threading.Event()
        self._errors_in_row = 0
        self._last_purge: datetime | None = None
        self.iterations = 0

    def stop(self) -> None:
        self.stop_event.set()

    def run_iteration(self) -> bool:
        """One pass. Returns True when any work was done."""
        inbound: RunSummary = self._worker.run_once(limit=self._settings.batch_size)
        outbound = self._relay.run_once(limit=self._settings.batch_size) if self._relay else RunSummary()
        if self._purge is not None:
            now = self._clock()
            due = self._last_purge is None or (now - self._last_purge).total_seconds() >= self._settings.purge_interval_seconds
            if due:
                counts = self._purge(now - self._settings.retention)
                self._last_purge = now
                self._metrics.inc("retention_purged_inbound", counts.get("inbound", 0))
                self._metrics.inc("retention_purged_outbox", counts.get("outbox", 0))
        self._metrics.heartbeat("integration_service", self._clock())
        return bool(inbound.claimed or outbound.claimed)

    def backoff_seconds(self) -> float:
        s = self._settings
        return min(s.error_backoff_max_seconds, s.error_backoff_base_seconds * 2 ** max(0, self._errors_in_row - 1))

    def run(self) -> None:
        logger.info("integration service started")
        while not self.stop_event.is_set():
            self.iterations += 1
            try:
                busy = self.run_iteration()
                self._errors_in_row = 0
                if not busy:
                    self.stop_event.wait(self._settings.poll_interval_seconds)
            except Exception as exc:  # noqa: BLE001 - the loop must survive
                self._errors_in_row += 1
                self._metrics.inc("service_errors", type=type(exc).__name__)
                logger.warning("integration service iteration failed type=%s (attempt %s)",
                               type(exc).__name__, self._errors_in_row)
                self.stop_event.wait(self.backoff_seconds())
        logger.info("integration service stopped")


def build_outbound_senders(rt, *, transport=None) -> tuple[dict, list[str]]:
    """Senders the outbox relay may use, plus a plain-language note for every
    protocol that has none. A sender is registered ONLY when its vendor
    endpoint is configured AND the protocol adapter is not BLOCKED, so the
    relay never dead-letters rows for want of an approved profile: they stay
    PENDING and the dashboard reports them as queued without a sender."""
    from app.integrations.adapters.base import AdapterReadiness
    from app.integrations.adapters.htng.sender import HtngSoapSender
    from app.integrations.core.envelope import Protocol
    from app.integrations.transport.soap import SoapEndpoint, SoapTransport, SoapVersion

    s = rt.settings
    senders: dict = {}
    notes: list[str] = []
    url = s.HTNG_OUTBOUND_ENDPOINT_URL
    htng_status = rt.htng_adapter.status() if rt.htng_adapter is not None else None
    if not url:
        notes.append("htng: no outbound vendor endpoint configured (HF-24); HTNG outbox rows stay PENDING")
    elif htng_status is None or htng_status.readiness is AdapterReadiness.BLOCKED:
        notes.append("htng: outbound endpoint configured but the HTNG adapter is BLOCKED "
                     f"({', '.join(htng_status.blocking_decisions) if htng_status else 'no adapter'}); "
                     "HTNG outbox rows stay PENDING")
    else:
        endpoint = SoapEndpoint(url=url, version=SoapVersion(s.HTNG_OUTBOUND_SOAP_VERSION),
                                timeout_seconds=s.HTNG_OUTBOUND_TIMEOUT_SECONDS)
        senders[Protocol.HTNG] = HtngSoapSender(transport or SoapTransport(), endpoint, rt.htng_adapter)
    notes.append("fias: outbound delivery needs a running FIAS link and approved link rules (HF-06, HF-11); "
                 "FIAS outbox rows stay PENDING")
    return senders, notes


def main() -> int:  # pragma: no cover - process entry point
    from app.integrations.core.retry import RetryPolicy, full_jitter
    from app.integrations.exchange.dispatcher import MessageDispatcher
    from app.integrations.runtime import get_runtime
    from app.integrations.transport.link_runtime import LinkNotStartable, build_fias_link_supervisor

    rt = get_runtime()
    s = rt.settings
    if not s.ENABLED:
        print("integration service not started: INTEGRATION_ENABLED is false")
        return 3
    link = None
    if s.FIAS_LINK_ENABLED:
        try:
            link = build_fias_link_supervisor(rt)
        except LinkNotStartable as exc:
            # Fail fast and visibly: an enabled link that cannot be built from
            # approved contracts is a configuration error, not something to skip.
            print(f"integration service not started: FIAS link not startable: {exc}")
            return 4
    policy = RetryPolicy(max_attempts=s.RETRY_MAX_ATTEMPTS, base_delay_seconds=s.RETRY_BASE_SECONDS,
                         max_delay_seconds=s.RETRY_MAX_SECONDS, jitter=full_jitter)
    worker = InboundWorker(repository=rt.repository, dispatcher=MessageDispatcher(rt.gateway.handlers),
                           policy=policy, lease_seconds=s.WORKER_LEASE_SECONDS, metrics=rt.metrics)
    senders, notes = build_outbound_senders(rt)
    for note in notes:
        logger.info("outbound: %s", note)
    relay = OutboxRelay(repository=rt.repository, adapters=rt.gateway.adapters, senders=senders, policy=policy,
                        lease_seconds=s.WORKER_LEASE_SECONDS, metrics=rt.metrics) if senders else None
    service = IntegrationService(
        worker=worker, relay=relay, metrics=rt.metrics,
        settings=ServiceSettings(retention=timedelta(days=s.RETENTION_DAYS) if s.RETENTION_DAYS else None),
        purge=lambda before: rt.repository.purge_completed(before=before, now=utcnow()),
    )
    signal.signal(signal.SIGTERM, lambda *_: service.stop())
    signal.signal(signal.SIGINT, lambda *_: service.stop())
    if link is not None:
        link.start()
    try:
        service.run()
    finally:
        if link is not None:
            link.stop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
