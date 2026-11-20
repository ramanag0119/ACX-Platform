"""Server-side TCP link (HMS listens): allow-list, single owner, framing, pump."""

from __future__ import annotations

import asyncio

import pytest

from app.integrations.core.errors import TransportNotConnected
from app.integrations.transport.framing import DelimitedFramer
from app.integrations.transport.tcp import LinkPump, LinkState
from app.integrations.transport.tcp_server import TcpListenerLink

STX, ETX = b"\x02", b"\x03"  # TEST ASSUMPTION markers


def framer():
    return DelimitedFramer(start=STX, end=ETX, max_frame_bytes=64)


def run(coro):
    return asyncio.run(asyncio.wait_for(coro, 15))


async def connect(port):
    return await asyncio.open_connection("127.0.0.1", port)


async def wait_for(pred, timeout=2.0):
    for _ in range(int(timeout / 0.01)):
        if pred():
            return True
        await asyncio.sleep(0.01)
    return False


def test_empty_allow_list_refused():
    with pytest.raises(ValueError):
        TcpListenerLink("127.0.0.1", 0, framer, allowed_peers=[])


def test_allowed_peer_frames_are_queued_and_replies_sent():
    async def go():
        link = TcpListenerLink("127.0.0.1", 0, framer, allowed_peers=["127.0.0.0/8"], read_timeout=0.2)
        port = await link.start()
        r, w = await connect(port)
        w.write(STX + b"one" + ETX + STX + b"tw")
        await w.drain()
        assert await asyncio.wait_for(link.inbound.get(), 2) == b"one"
        w.write(b"o" + ETX)
        await w.drain()
        assert await asyncio.wait_for(link.inbound.get(), 2) == b"two"
        assert link.health.state is LinkState.CONNECTED
        await link.send(b"reply")
        assert await asyncio.wait_for(r.readexactly(7), 2) == STX + b"reply" + ETX
        w.close()
        assert await wait_for(lambda: link.health.state is LinkState.DISCONNECTED)
        with pytest.raises(TransportNotConnected):
            await link.send(b"x")
        await link.stop()
        assert link.health.state is LinkState.CLOSED
    run(go())


def test_peer_not_in_allow_list_is_dropped():
    async def go():
        link = TcpListenerLink("127.0.0.1", 0, framer, allowed_peers=["10.9.8.7/32"])
        port = await link.start()
        r, w = await connect(port)
        assert await asyncio.wait_for(r.read(10), 2) == b""  # closed by server
        assert link.health.rejected_peers == 1 and link.inbound.empty()
        await link.stop()
    run(go())


def test_second_connection_rejected_while_link_busy_and_reconnect_allowed():
    async def go():
        link = TcpListenerLink("127.0.0.1", 0, framer, allowed_peers=["127.0.0.1"], read_timeout=0.2)
        port = await link.start()
        _, w1 = await connect(port)
        assert await wait_for(lambda: link.health.state is LinkState.CONNECTED)
        r2, _ = await connect(port)
        assert await asyncio.wait_for(r2.read(10), 2) == b""
        assert link.health.rejected_busy == 1
        w1.close()
        assert await wait_for(lambda: link.health.state is LinkState.DISCONNECTED)
        _, w3 = await connect(port)
        w3.write(STX + b"again" + ETX)
        await w3.drain()
        assert await asyncio.wait_for(link.inbound.get(), 2) == b"again"
        assert link.health.connections == 2
        w3.close()
        await link.stop()
    run(go())


def test_listener_works_with_link_pump():
    async def go():
        link = TcpListenerLink("127.0.0.1", 0, framer, allowed_peers=["127.0.0.1"], read_timeout=0.2)
        port = await link.start()
        seen = []
        stop = asyncio.Event()
        pump = LinkPump(link, lambda f: seen.append(f) or "ok", responder=lambda result: b"ack")
        task = asyncio.create_task(pump.run(stop=stop))
        r, w = await connect(port)
        w.write(STX + b"msg" + ETX)
        await w.drain()
        assert await asyncio.wait_for(r.readexactly(5), 2) == STX + b"ack" + ETX
        assert seen == [b"msg"]
        stop.set()
        await asyncio.wait_for(task, 2)
        w.close()
        await link.stop()
    run(go())


def test_oversized_frame_from_peer_does_not_kill_link():
    async def go():
        link = TcpListenerLink("127.0.0.1", 0, framer, allowed_peers=["127.0.0.1"], read_timeout=0.2)
        port = await link.start()
        _, w = await connect(port)
        w.write(STX + b"x" * 200 + ETX + STX + b"ok" + ETX)
        await w.drain()
        assert await asyncio.wait_for(link.inbound.get(), 2) == b"ok"
        assert link.health.framing_errors >= 1 and link.health.state is LinkState.CONNECTED
        w.close()
        await link.stop()
    run(go())
