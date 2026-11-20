"""Process wiring for a FIAS TCP link: lifecycle, shutdown and health.

`LinkSupervisor` runs ONE link (client `TcpLink` or server `TcpListenerLink`)
and its `LinkPump` on a dedicated asyncio event loop in a background thread,
so the synchronous integration service loop is not blocked:

    start()   build the link inside the loop, start it, start the pump
    stop()    stop the pump (no new frame is taken), stop the link (sockets
              closed, listener closed), join the thread -- bounded by a timeout
    health()  the link's TransportHealth plus `running` / `mode`

`build_fias_link_supervisor()` is the PRODUCTION builder used by the
integration service. It refuses (raises `LinkNotStartable`) unless every
contract the link depends on is approved:

* the FIAS adapter is READY -- i.e. a VERIFIED FIAS specification is loaded
  (HF-11). Today `PRODUCTION_SPECIFICATION is None`, so it is BLOCKED;
* a VERIFIED framing for the link exists (HF-06). Today there is none:
  `VERIFIED_FIAS_FRAMER_FACTORY` is None. The provisional 0x02/0x03 markers in
  `simulators/fixtures.py` are a TEST assumption and are never used here.

No ACK, NAK, heartbeat, handshake or resynchronisation is sent: those rules are
not specified (HF-06). The supervisor itself is protocol-neutral and is
exercised in tests with the provisional TEST framer and specification only.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Any

from app.integrations.adapters.base import AdapterReadiness, TransportContext
from app.integrations.core.envelope import Protocol
from app.integrations.transport.framing import Framer
from app.integrations.transport.tcp import LinkPump, TcpLink, TcpSettings
from app.integrations.transport.tcp_server import TcpListenerLink

logger = logging.getLogger("hms.integrations.link")

#: The verified FIAS framing (HF-06). None until the vendor's link document is
#: approved; a production FIAS link cannot be built without it.
VERIFIED_FIAS_FRAMER_FACTORY: Callable[[], Framer] | None = None


class LinkNotStartable(RuntimeError):
    """The link cannot be started from approved contracts. The message names the
    missing decision(s); nothing is started."""


class LinkSupervisor:
    def __init__(
        self,
        *,
        name: str,
        mode: str,
        link_factory: Callable[[], Any],
        receive: Callable[[bytes], object],
        responder: Callable[[object], bytes | None] | None = None,
        pump_retry_base_seconds: float = 0.5,
        pump_retry_max_seconds: float = 30.0,
    ) -> None:
        if mode not in ("client", "listener"):
            raise ValueError("mode must be 'client' or 'listener'")
        self.name = name
        self.mode = mode
        self._link_factory = link_factory
        self._receive = receive
        self._responder = responder
        self._retry_base = pump_retry_base_seconds
        self._retry_max = pump_retry_max_seconds
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Event | None = None
        self._started = threading.Event()
        self._start_error: BaseException | None = None
        self.link: Any = None
        self.pump: LinkPump | None = None
        self.port: int | None = None

    # ------------------------------------------------------------- lifecycle
    def start(self, *, timeout: float = 10.0) -> None:
        if self._thread is not None:
            raise RuntimeError("link supervisor already started")
        self._thread = threading.Thread(target=self._thread_main, name=f"link-{self.name}", daemon=True)
        self._thread.start()
        if not self._started.wait(timeout):
            raise LinkNotStartable(f"link {self.name} did not start within {timeout}s")
        if self._start_error is not None:
            raise LinkNotStartable(f"link {self.name} failed to start: {type(self._start_error).__name__}")
        logger.info("link supervisor started name=%s mode=%s", self.name, self.mode)

    def stop(self, *, timeout: float = 10.0) -> bool:
        """Stop the pump, then the link, then join the thread. True when the
        thread ended inside `timeout`."""
        loop, stop = self._loop, self._stop
        if loop is not None and stop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(stop.set)
        if self._thread is None:
            return True
        self._thread.join(timeout)
        ended = not self._thread.is_alive()
        logger.info("link supervisor stopped name=%s clean=%s", self.name, ended)
        return ended

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def health(self) -> dict:
        base = self.link.health.as_dict() if self.link is not None else {"state": "not_started"}
        return {**base, "mode": self.mode, "running": self.running,
                "frames_processed": self.pump.processed if self.pump else 0,
                "intake_retries": self.pump.intake_retries if self.pump else 0}

    # ------------------------------------------------------------- internals
    def _thread_main(self) -> None:
        try:
            asyncio.run(self._main())
        except BaseException as exc:  # noqa: BLE001 - reported through start()
            self._start_error = self._start_error or exc
            self._started.set()

    async def _main(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        try:
            self.link = self._link_factory()
            tasks = []
            if isinstance(self.link, TcpListenerLink):
                self.port = await self.link.start()
            else:
                tasks.append(asyncio.create_task(self.link.run(), name=f"{self.name}-link"))
            self.pump = LinkPump(self.link, self._receive, responder=self._responder,
                                 retry_base_seconds=self._retry_base, retry_max_seconds=self._retry_max)
            pump_task = asyncio.create_task(self.pump.run(stop=self._stop), name=f"{self.name}-pump")
        except BaseException as exc:
            self._start_error = exc
            self._started.set()
            raise
        self._started.set()
        await self._stop.wait()
        # Shutdown order: the pump first (no new frame is taken; a frame still
        # being retried is left unacknowledged), then the link (sockets closed).
        await asyncio.gather(pump_task, return_exceptions=True)
        await self.link.stop()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def build_fias_link_supervisor(rt, *, framer_factory: Callable[[], Framer] | None = None) -> LinkSupervisor:
    """Production builder (see module docstring). Raises LinkNotStartable with
    the missing decision instead of guessing any FIAS link rule."""
    s = rt.settings
    if not s.FIAS_LINK_ENABLED:
        raise LinkNotStartable("FIAS link is not enabled (INTEGRATION_FIAS_LINK_ENABLED=false)")
    statuses = [st for st in rt.gateway.adapters.statuses() if str(st.protocol) == str(Protocol.FIAS)]
    adapter = statuses[0] if statuses else None
    if adapter is None or adapter.readiness is not AdapterReadiness.READY:
        blocking = ", ".join(adapter.blocking_decisions) if adapter else "no FIAS adapter"
        raise LinkNotStartable(
            f"FIAS adapter is not READY ({adapter.readiness if adapter else 'absent'}); "
            f"a verified FIAS specification is required ({blocking or 'HF-11'})")
    framer_factory = framer_factory or VERIFIED_FIAS_FRAMER_FACTORY
    if framer_factory is None:
        raise LinkNotStartable("No verified FIAS framing / link rules (HF-06); the link cannot be built")

    client = rt.gateway.authenticate(s.FIAS_LINK_CLIENT_CODE, s.FIAS_LINK_CLIENT_SECRET, protocol=Protocol.FIAS)
    peer = f"{s.FIAS_LINK_HOST}:{s.FIAS_LINK_PORT}" if s.FIAS_LINK_MODE == "client" else None
    context = TransportContext(transport="tcp", peer=peer)

    def receive(frame: bytes):
        return rt.gateway.receive(frame, protocol=Protocol.FIAS, client=client, context=context)

    if s.FIAS_LINK_MODE == "client":
        def link_factory():
            return TcpLink(TcpSettings(host=s.FIAS_LINK_HOST, port=s.FIAS_LINK_PORT), framer_factory)
    else:
        def link_factory():
            return TcpListenerLink("0.0.0.0", s.FIAS_LINK_PORT, framer_factory,  # noqa: S104 - allow-listed
                                   allowed_peers=list(s.FIAS_LINK_ALLOWED_PEERS))
    # No protocol responder (ACK/NAK) is passed: none exists until HF-06 defines one.
    return LinkSupervisor(name="fias", mode=s.FIAS_LINK_MODE, link_factory=link_factory, receive=receive)


__all__ = ["LinkNotStartable", "LinkSupervisor", "VERIFIED_FIAS_FRAMER_FACTORY", "build_fias_link_supervisor"]
