"""Asyncio TCP transport.

    FramedStream  one connected socket + a Framer + read/write timeouts.
                  Used for both sides (client links, and the test simulator's
                  accepted connections).
    open_tcp()    connect with a timeout -> FramedStream.
    TcpLink       supervised CLIENT link: connect, read frames into a bounded
                  queue (backpressure), reconnect with bounded back-off,
                  graceful stop, health reporting.
    LinkPump      takes frames off a TcpLink and hands them to the
                  ExchangeAdapter in a worker thread, optionally writing a
                  protocol response.

Which side listens (HMS or the PMS), keep-alive/heartbeat records and session
start-up records are FIAS link rules that are NOT verified (HF-06), so
nothing here sends anything on its own: no heartbeat, no handshake, no ACK.
A protocol-specific `responder` can be supplied once those rules are known.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.integrations.core.envelope import utcnow
from app.integrations.core.errors import (
    ConnectionClosed,
    ConnectTimeout,
    IntegrationError,
    ProtocolError,
    ReadTimeout,
    TransportError,
    TransportNotConnected,
    WriteTimeout,
)
from app.integrations.transport.framing import Framer

logger = logging.getLogger("hms.integrations.tcp")


class LinkState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CLOSED = "closed"


@dataclass
class TransportHealth:
    state: LinkState = LinkState.DISCONNECTED
    connected_since: datetime | None = None
    last_error_code: str | None = None
    last_error_at: datetime | None = None
    reconnect_attempts: int = 0
    connections: int = 0
    frames_received: int = 0
    frames_sent: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0
    framing_errors: int = 0
    read_timeouts: int = 0

    def record_error(self, error: IntegrationError) -> None:
        self.last_error_code = error.code
        self.last_error_at = utcnow()

    def as_dict(self) -> dict:
        return {
            "state": str(self.state),
            "connected_since": self.connected_since.isoformat() if self.connected_since else None,
            "last_error_code": self.last_error_code,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "reconnect_attempts": self.reconnect_attempts,
            "connections": self.connections,
            "frames_received": self.frames_received,
            "frames_sent": self.frames_sent,
            "bytes_received": self.bytes_received,
            "bytes_sent": self.bytes_sent,
            "framing_errors": self.framing_errors,
            "read_timeouts": self.read_timeouts,
        }


@dataclass(frozen=True)
class ReconnectPolicy:
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    multiplier: float = 2.0
    #: None = keep trying until stopped.
    max_attempts: int | None = None

    def delay_for(self, attempt: int) -> float:
        return min(self.max_delay_seconds, self.base_delay_seconds * self.multiplier ** max(0, attempt - 1))


@dataclass(frozen=True)
class TcpSettings:
    host: str
    port: int
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    write_timeout: float = 5.0
    read_chunk_bytes: int = 4096
    inbound_queue_size: int = 100
    reconnect: ReconnectPolicy = field(default_factory=ReconnectPolicy)

    def __post_init__(self) -> None:
        if not (0 < self.port < 65536):
            raise ValueError("port out of range")
        for name in ("connect_timeout", "read_timeout", "write_timeout"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.read_chunk_bytes < 1 or self.inbound_queue_size < 1:
            raise ValueError("read_chunk_bytes and inbound_queue_size must be positive")


class FramedStream:
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        framer: Framer,
        *,
        read_timeout: float,
        write_timeout: float,
        read_chunk_bytes: int = 4096,
        health: TransportHealth | None = None,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._framer = framer
        self._read_timeout = read_timeout
        self._write_timeout = write_timeout
        self._chunk = read_chunk_bytes
        self.health = health or TransportHealth()
        self._frames: deque[bytes] = deque()
        self._errors: deque[ProtocolError] = deque()
        self._send_lock = asyncio.Lock()
        self._recv_lock = asyncio.Lock()
        self._closed = False

    @property
    def peer(self) -> str | None:
        info = self._writer.get_extra_info("peername")
        return f"{info[0]}:{info[1]}" if info else None

    @property
    def closed(self) -> bool:
        return self._closed

    async def send(self, payload: bytes) -> None:
        if self._closed:
            raise TransportNotConnected("Stream is closed.")
        data = self._framer.frame(payload)
        async with self._send_lock:
            try:
                self._writer.write(data)
                await asyncio.wait_for(self._writer.drain(), self._write_timeout)
            except TimeoutError:
                raise WriteTimeout("Write timed out.") from None
            except (ConnectionError, OSError):
                raise ConnectionClosed("Connection closed while writing.") from None
        self.health.frames_sent += 1
        self.health.bytes_sent += len(data)

    async def receive(self) -> bytes:
        """Next whole frame. Frames already decoded are returned before any
        queued framing error is raised."""
        async with self._recv_lock:
            while True:
                if self._frames:
                    return self._frames.popleft()
                if self._errors:
                    raise self._errors.popleft()
                if self._closed:
                    raise ConnectionClosed("Stream is closed.")
                try:
                    chunk = await asyncio.wait_for(self._reader.read(self._chunk), self._read_timeout)
                except TimeoutError:
                    self.health.read_timeouts += 1
                    raise ReadTimeout("Read timed out.") from None
                except (ConnectionError, OSError):
                    raise ConnectionClosed("Connection reset.") from None
                if not chunk:
                    raise ConnectionClosed("Peer closed the connection.")
                self.health.bytes_received += len(chunk)
                frames = self._framer.feed(chunk)
                errors = self._framer.take_errors()
                self.health.frames_received += len(frames)
                self.health.framing_errors += len(errors)
                self._frames.extend(frames)
                self._errors.extend(errors)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._framer.reset()
        self._writer.close()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(self._writer.wait_closed(), 2.0)


async def open_tcp(
    settings: TcpSettings, framer: Framer, *, health: TransportHealth | None = None
) -> FramedStream:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(settings.host, settings.port), settings.connect_timeout
        )
    except TimeoutError:
        raise ConnectTimeout("Connect timed out.") from None
    except OSError:
        raise TransportError("Connection failed.", code="connect_failed") from None
    return FramedStream(
        reader,
        writer,
        framer,
        read_timeout=settings.read_timeout,
        write_timeout=settings.write_timeout,
        read_chunk_bytes=settings.read_chunk_bytes,
        health=health,
    )


class TcpLink:
    def __init__(
        self,
        settings: TcpSettings,
        framer_factory: Callable[[], Framer],
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.settings = settings
        self._framer_factory = framer_factory
        self._sleep = sleep
        self.health = TransportHealth()
        self.inbound: asyncio.Queue[bytes] = asyncio.Queue(maxsize=settings.inbound_queue_size)
        self._stream: FramedStream | None = None
        self._stop = asyncio.Event()
        self._connected = asyncio.Event()

    async def wait_connected(self, timeout: float) -> None:
        await asyncio.wait_for(self._connected.wait(), timeout)

    async def send(self, payload: bytes) -> None:
        stream = self._stream
        if stream is None or stream.closed or self.health.state is not LinkState.CONNECTED:
            raise TransportNotConnected("Link is not connected.")
        await stream.send(payload)

    async def stop(self) -> None:
        self._stop.set()
        if self._stream is not None:
            await self._stream.close()

    async def run(self) -> None:
        """Run until `stop()` or the reconnect budget is exhausted."""
        attempt = 0
        try:
            while not self._stop.is_set():
                self.health.state = LinkState.CONNECTING
                try:
                    self._stream = await open_tcp(self.settings, self._framer_factory(), health=self.health)
                except TransportError as exc:
                    self.health.record_error(exc)
                    attempt += 1
                    self.health.reconnect_attempts = attempt
                    if not await self._backoff(attempt):
                        return
                    continue

                attempt = 0
                self.health.reconnect_attempts = 0
                self.health.connections += 1
                self.health.state = LinkState.CONNECTED
                self.health.connected_since = utcnow()
                self._connected.set()
                logger.info("tcp link connected peer=%s", self._stream.peer)
                await self._read_loop(self._stream)
                self._connected.clear()
                await self._stream.close()
                if self._stop.is_set():
                    return
                self.health.state = LinkState.DISCONNECTED
                attempt += 1
                self.health.reconnect_attempts = attempt
                if not await self._backoff(attempt):
                    return
        finally:
            self._connected.clear()
            if self._stream is not None:
                await self._stream.close()
            self.health.state = LinkState.CLOSED

    async def _backoff(self, attempt: int) -> bool:
        policy = self.settings.reconnect
        if policy.max_attempts is not None and attempt > policy.max_attempts:
            logger.warning("tcp link giving up after %s attempts", attempt - 1)
            return False
        self.health.state = LinkState.DISCONNECTED
        stop_wait = asyncio.ensure_future(self._stop.wait())
        sleeper = asyncio.ensure_future(self._sleep(policy.delay_for(attempt)))
        done, pending = await asyncio.wait({stop_wait, sleeper}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        return not self._stop.is_set()

    async def _read_loop(self, stream: FramedStream) -> None:
        while not self._stop.is_set():
            try:
                frame = await stream.receive()
            except ReadTimeout as exc:
                # An idle link is not an error until heartbeat rules are known (HF-06).
                self.health.record_error(exc)
                continue
            except ProtocolError as exc:
                self.health.record_error(exc)
                continue
            except TransportError as exc:
                if not self._stop.is_set():
                    self.health.record_error(exc)
                return
            # Backpressure: blocks (and therefore stops reading the socket,
            # letting TCP flow control push back) while the consumer is behind.
            await self.inbound.put(frame)


class LinkOutboundSender:
    """OutboxRelay sender for a TcpLink.

    The relay is synchronous (it runs in a worker thread); the link lives on
    an event loop. `send` schedules the write on that loop and waits for it,
    so a dead link surfaces as a TRANSIENT TransportError and the outbox row
    is retried.
    """

    def __init__(self, link: TcpLink, loop: asyncio.AbstractEventLoop, *, timeout: float = 10.0) -> None:
        self._link = link
        self._loop = loop
        self._timeout = timeout

    def send(self, payload: bytes, *, claim) -> None:  # noqa: ARG002 - interface
        future = asyncio.run_coroutine_threadsafe(self._link.send(payload), self._loop)
        try:
            future.result(self._timeout)
        except TimeoutError:
            future.cancel()
            raise WriteTimeout("Outbound write timed out.") from None


Responder = Callable[[object], bytes | None]


def _is_transient(result: object) -> bool:
    return bool(getattr(result, "retryable", False))


class LinkPump:
    """Moves frames from a TcpLink into the exchange.

    `receive` is the (blocking, DB-touching) ExchangeAdapter.receive bound to a
    client and context; it runs in a thread so the event loop keeps reading.
    """

    def __init__(
        self,
        link: TcpLink,
        receive: Callable[[bytes], object],
        *,
        responder: Responder | None = None,
        retry_base_seconds: float = 0.5,
        retry_max_seconds: float = 30.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._link = link
        self._receive = receive
        self._responder = responder
        self._retry_base = retry_base_seconds
        self._retry_max = retry_max_seconds
        self._sleep = sleep
        self.processed = 0
        self.intake_retries = 0
        self.unprocessed_on_stop = 0

    async def _receive_with_retry(self, frame: bytes, stop: asyncio.Event) -> object | None:
        """Hand one frame to the exchange; retry it while intake fails TRANSIENTLY.

        A database outage must not turn a valid frame into a rejection that is
        silently dropped. The same frame is retried with bounded back-off and
        no further frame is taken meanwhile (order kept; the bounded queue and
        TCP flow control push back on the sender). If the pump is stopped
        before the frame is accepted, None is returned and the frame is NOT
        acknowledged -- re-delivery is then the sender's responsibility under
        the protocol's acknowledgement rules (HF-06)."""
        attempt = 0
        while True:
            try:
                result = await asyncio.to_thread(self._receive, frame)
            except Exception:  # noqa: BLE001 - an intake crash is treated as transient
                logger.exception("link pump intake raised; frame will be retried")
                result = None
            if result is not None and not _is_transient(result):
                return result
            attempt += 1
            self.intake_retries += 1
            delay = min(self._retry_max, self._retry_base * 2 ** (attempt - 1))
            stopper = asyncio.ensure_future(stop.wait())
            sleeper = asyncio.ensure_future(self._sleep(delay))
            done, pending = await asyncio.wait({stopper, sleeper}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            if stop.is_set():
                return None

    async def run(self, *, stop: asyncio.Event) -> None:
        while not stop.is_set():
            get = asyncio.ensure_future(self._link.inbound.get())
            stopper = asyncio.ensure_future(stop.wait())
            done, pending = await asyncio.wait({get, stopper}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            if get not in done:
                return
            frame = get.result()
            result = await self._receive_with_retry(frame, stop)
            if result is None:  # stopped while the database was still failing
                self.unprocessed_on_stop += 1
                return
            self.processed += 1
            if self._responder is not None:
                reply = self._responder(result)
                if reply is not None:
                    with contextlib.suppress(TransportError):
                        await self._link.send(reply)
