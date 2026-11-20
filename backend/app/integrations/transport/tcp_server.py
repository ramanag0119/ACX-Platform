"""Server-side TCP link: HMS listens and the PMS connects.

Whether HMS is the listening side is a FIAS operational rule that is not
verified (HF-06); this component exists so either answer can be
served without new transport code. It carries no protocol semantics: no
handshake, heartbeat or acknowledgement is sent on its own.

Safety rules:
* `allowed_peers` (IP addresses or CIDR networks) is REQUIRED; an empty list
  refuses to start. Connections from other addresses are closed immediately.
* One active connection per link. A second connection while one is active
  is closed (the PMS link has a single owner).
* Same `inbound` queue / `send` / `health` surface as `TcpLink`, so
  `LinkPump` and `LinkOutboundSender` work unchanged.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
from collections.abc import Callable

from app.integrations.core.envelope import utcnow
from app.integrations.core.errors import ProtocolError, ReadTimeout, TransportError, TransportNotConnected
from app.integrations.transport.framing import Framer
from app.integrations.transport.tcp import FramedStream, LinkState, TransportHealth

logger = logging.getLogger("hms.integrations.tcp_server")


class ListenerHealth(TransportHealth):
    def __init__(self) -> None:
        super().__init__()
        self.rejected_peers = 0
        self.rejected_busy = 0

    def as_dict(self) -> dict:
        return {**super().as_dict(), "rejected_peers": self.rejected_peers, "rejected_busy": self.rejected_busy}


class TcpListenerLink:
    def __init__(
        self,
        host: str,
        port: int,
        framer_factory: Callable[[], Framer],
        *,
        allowed_peers: list[str],
        read_timeout: float = 30.0,
        write_timeout: float = 5.0,
        inbound_queue_size: int = 100,
    ) -> None:
        if not allowed_peers:
            raise ValueError("allowed_peers is required: a listener never accepts any address")
        self._networks = [ipaddress.ip_network(p, strict=False) for p in allowed_peers]
        self.host = host
        self.port = port
        self._framer_factory = framer_factory
        self._read_timeout = read_timeout
        self._write_timeout = write_timeout
        self.health = ListenerHealth()
        self.inbound: asyncio.Queue[bytes] = asyncio.Queue(maxsize=inbound_queue_size)
        self._server: asyncio.base_events.Server | None = None
        self._active: FramedStream | None = None
        self._stopping = False

    def _allowed(self, peer_ip: str | None) -> bool:
        if not peer_ip:
            return False
        try:
            addr = ipaddress.ip_address(peer_ip)
        except ValueError:
            return False
        return any(addr in net for net in self._networks)

    async def start(self) -> int:
        self._server = await asyncio.start_server(self._on_client, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]
        self.health.state = LinkState.DISCONNECTED  # listening, no peer yet
        return self.port

    async def _on_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        peer_ip = peer[0] if peer else None
        if self._stopping or not self._allowed(peer_ip):
            self.health.rejected_peers += 1
            logger.warning("tcp listener rejected peer (not allow-listed)")
            writer.close()
            return
        if self._active is not None and not self._active.closed:
            self.health.rejected_busy += 1
            logger.warning("tcp listener rejected second connection (link busy)")
            writer.close()
            return
        stream = FramedStream(reader, writer, self._framer_factory(), read_timeout=self._read_timeout,
                              write_timeout=self._write_timeout, health=self.health)
        self._active = stream
        self.health.connections += 1
        self.health.state = LinkState.CONNECTED
        self.health.connected_since = utcnow()
        try:
            while not self._stopping:
                try:
                    frame = await stream.receive()
                except (ReadTimeout, ProtocolError) as exc:
                    self.health.record_error(exc)
                    continue
                except TransportError as exc:
                    if not self._stopping:
                        self.health.record_error(exc)
                    break
                await self.inbound.put(frame)
        finally:
            await stream.close()
            if self._active is stream:
                self._active = None
                if not self._stopping:
                    self.health.state = LinkState.DISCONNECTED

    async def send(self, payload: bytes) -> None:
        stream = self._active
        if stream is None or stream.closed:
            raise TransportNotConnected("No peer is connected.")
        await stream.send(payload)

    async def stop(self) -> None:
        self._stopping = True
        if self._active is not None:
            await self._active.close()
        if self._server is not None:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()
        self.health.state = LinkState.CLOSED
