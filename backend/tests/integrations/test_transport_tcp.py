"""TCP transport: framing and real loopback sockets (no FIAS semantics)."""

from __future__ import annotations

import asyncio
import contextlib

import pytest

from app.integrations.core.errors import (
    ConnectionClosed,
    ConnectTimeout,
    FrameTooLarge,
    ProtocolError,
    ReadTimeout,
    TransportError,
    TransportNotConnected,
)
from app.integrations.transport.framing import DelimitedFramer
from app.integrations.transport.tcp import (
    FramedStream,
    LinkState,
    ReconnectPolicy,
    TcpLink,
    TcpSettings,
    open_tcp,
)

STX, ETX = b"\x02", b"\x03"  # TEST ASSUMPTION markers (see simulators/fixtures.py)


def framer(max_frame=64):
    return DelimitedFramer(start=STX, end=ETX, max_frame_bytes=max_frame)


# --- framing ---------------------------------------------------------------
def test_framing_requires_explicit_markers():
    with pytest.raises(TypeError):
        DelimitedFramer()  # no vendor default exists
    with pytest.raises(ValueError):
        DelimitedFramer(end=b"")


def test_partial_reads_are_reassembled():
    f = framer()
    assert f.feed(STX + b"AB") == []
    assert f.feed(b"CD") == []
    assert f.feed(ETX) == [b"ABCD"]
    assert f.buffered == 0


def test_multiple_frames_in_one_read():
    f = framer()
    assert f.feed(STX + b"one" + ETX + STX + b"two" + ETX + STX + b"thr") == [b"one", b"two"]
    assert f.feed(b"ee" + ETX) == [b"three"]


def test_byte_at_a_time():
    f = framer()
    out = []
    for b in STX + b"slow" + ETX:
        out += f.feed(bytes([b]))
    assert out == [b"slow"]


def test_empty_payload_frame_is_delivered_for_rejection_upstream():
    assert framer().feed(STX + ETX) == [b""]


def test_noise_is_discarded_and_counted():
    f = framer()
    assert f.feed(b"garbage" + STX + b"ok" + ETX + b"tail") == [b"ok"]
    assert f.stats.discarded_bytes >= 7


def test_resync_on_second_start_marker():
    f = framer()
    assert f.feed(STX + b"trunc" + STX + b"good" + ETX) == [b"good"]
    assert f.stats.resyncs == 1


def test_oversized_unterminated_input_is_dropped_without_losing_good_frames():
    f = framer(max_frame=8)
    frames = f.feed(STX + b"ok" + ETX + STX + b"x" * 50)
    assert frames == [b"ok"]
    errors = f.take_errors()
    assert len(errors) == 1 and isinstance(errors[0], FrameTooLarge)
    assert f.buffered == 0
    assert f.feed(STX + b"next" + ETX) == [b"next"]


def test_oversized_complete_frame_is_dropped():
    f = framer(max_frame=4)
    assert f.feed(STX + b"toolong" + ETX + STX + b"ok" + ETX) == [b"ok"]
    assert isinstance(f.take_errors()[0], FrameTooLarge)


def test_frame_refuses_payload_containing_markers_or_too_large():
    f = framer(max_frame=8)
    with pytest.raises(ProtocolError):
        f.frame(b"a" + ETX)
    with pytest.raises(ProtocolError):
        f.frame(STX + b"a")
    with pytest.raises(FrameTooLarge):
        f.frame(b"x" * 9)
    assert f.frame(b"ok") == STX + b"ok" + ETX


def test_end_only_framing():
    f = DelimitedFramer(end=b"\n")
    assert f.feed(b"a\nb\nc") == [b"a", b"b"]


# --- sockets ---------------------------------------------------------------
class EchoServer:
    """Loopback server; behaviour switched per test."""

    def __init__(self, mode="echo"):
        self.mode = mode
        self.server = None
        self.port = None
        self.writers = []
        self.received = bytearray()
        self.connections = 0

    async def start(self):
        self.server = await asyncio.start_server(self._client, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def _client(self, reader, writer):
        self.connections += 1
        self.writers.append(writer)
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                self.received.extend(data)
                if self.mode == "echo":
                    writer.write(data)
                    await writer.drain()
        except ConnectionError:
            pass
        finally:
            writer.close()

    async def drop_all(self):
        for w in self.writers:
            w.close()
        self.writers.clear()

    async def stop(self):
        await self.drop_all()
        self.server.close()
        await self.server.wait_closed()


def settings(port, **kw):
    base = dict(connect_timeout=1, read_timeout=0.5, write_timeout=1,
                reconnect=ReconnectPolicy(base_delay_seconds=0.05, max_delay_seconds=0.1))
    base.update(kw)
    return TcpSettings(host="127.0.0.1", port=port, **base)


def run(coro):
    return asyncio.run(asyncio.wait_for(coro, 15))


def test_send_receive_roundtrip_over_loopback():
    async def go():
        srv = await EchoServer().start()
        stream = await open_tcp(settings(srv.port), framer())
        await stream.send(b"hello")
        assert await stream.receive() == b"hello"
        assert stream.health.frames_sent == 1 and stream.health.frames_received == 1
        await stream.close()
        await srv.stop()
    run(go())


def test_connect_timeout(monkeypatch):
    async def hang(*a, **k):
        await asyncio.sleep(10)

    monkeypatch.setattr(asyncio, "open_connection", hang)
    with pytest.raises(ConnectTimeout):
        run(open_tcp(settings(9, connect_timeout=0.1), framer()))


def test_connection_refused_is_transport_error():
    async def go():
        srv = await EchoServer().start()
        port = srv.port
        await srv.stop()
        with pytest.raises(TransportError) as exc:
            await open_tcp(settings(port), framer())
        assert exc.value.code == "connect_failed"
    run(go())


def test_read_timeout():
    async def go():
        srv = await EchoServer(mode="silent").start()
        stream = await open_tcp(settings(srv.port, read_timeout=0.1), framer())
        with pytest.raises(ReadTimeout):
            await stream.receive()
        assert stream.health.read_timeouts == 1
        await stream.close()
        await srv.stop()
    run(go())


def test_peer_disconnect_raises_connection_closed_and_cleans_up():
    async def go():
        srv = await EchoServer(mode="silent").start()
        stream = await open_tcp(settings(srv.port, read_timeout=2), framer())
        await asyncio.sleep(0.05)
        await srv.drop_all()
        with pytest.raises(ConnectionClosed):
            await stream.receive()
        await stream.close()
        assert stream.closed
        with pytest.raises(TransportNotConnected):
            await stream.send(b"x")
        await srv.stop()
    run(go())


def test_framing_error_surfaces_after_good_frames():
    async def go():
        srv = await EchoServer(mode="silent").start()
        stream = await open_tcp(settings(srv.port, read_timeout=2), framer(max_frame=4))
        await asyncio.sleep(0.05)
        w = srv.writers[0]
        w.write(STX + b"ok" + ETX + STX + b"far-too-long" + ETX)
        await w.drain()
        assert await stream.receive() == b"ok"
        with pytest.raises(FrameTooLarge):
            await stream.receive()
        assert stream.health.framing_errors == 1
        await stream.close()
        await srv.stop()
    run(go())


def test_concurrent_send_and_receive():
    async def go():
        srv = await EchoServer().start()
        stream = await open_tcp(settings(srv.port, read_timeout=2), framer())
        payloads = [f"m{i}".encode() for i in range(50)]

        async def sender():
            await asyncio.gather(*(stream.send(p) for p in payloads))

        async def receiver():
            return [await stream.receive() for _ in payloads]

        _, got = await asyncio.gather(sender(), receiver())
        assert sorted(got) == sorted(payloads)  # frames never interleave/corrupt
        await stream.close()
        await srv.stop()
    run(go())


def test_link_reconnects_after_disconnect_and_stops_gracefully():
    async def go():
        srv = await EchoServer().start()
        link = TcpLink(settings(srv.port, read_timeout=0.2), framer)
        task = asyncio.create_task(link.run())
        await link.wait_connected(2)
        await link.send(b"first")
        assert await asyncio.wait_for(link.inbound.get(), 2) == b"first"
        await srv.drop_all()
        for _ in range(100):
            if link.health.connections >= 2 and link.health.state is LinkState.CONNECTED:
                break
            await asyncio.sleep(0.02)
        assert link.health.connections >= 2
        await link.send(b"second")
        assert await asyncio.wait_for(link.inbound.get(), 2) == b"second"
        await link.stop()
        await asyncio.wait_for(task, 2)
        assert link.health.state is LinkState.CLOSED
        with pytest.raises(TransportNotConnected):
            await link.send(b"after-stop")
        await srv.stop()
    run(go())


def test_link_gives_up_after_reconnect_budget():
    async def go():
        srv = await EchoServer().start()
        port = srv.port
        await srv.stop()
        link = TcpLink(settings(port, reconnect=ReconnectPolicy(base_delay_seconds=0.01, max_attempts=2)), framer)
        await asyncio.wait_for(link.run(), 3)
        assert link.health.state is LinkState.CLOSED
        assert link.health.last_error_code == "connect_failed"
    run(go())


def test_backpressure_bounded_queue_without_loss():
    async def go():
        srv = await EchoServer(mode="silent").start()
        link = TcpLink(settings(srv.port, read_timeout=0.2, inbound_queue_size=2), framer)
        task = asyncio.create_task(link.run())
        await link.wait_connected(2)
        w = srv.writers[0]
        w.write(b"".join(STX + f"f{i}".encode() + ETX for i in range(10)))
        await w.drain()
        await asyncio.sleep(0.2)
        assert link.inbound.qsize() == 2  # producer blocked, not dropping
        got = [await asyncio.wait_for(link.inbound.get(), 2) for _ in range(10)]
        assert got == [f"f{i}".encode() for i in range(10)]
        await link.stop()
        await asyncio.wait_for(task, 2)
        await srv.stop()
    run(go())


def test_idle_read_timeout_does_not_drop_link():
    async def go():
        srv = await EchoServer(mode="silent").start()
        link = TcpLink(settings(srv.port, read_timeout=0.05), framer)
        task = asyncio.create_task(link.run())
        await link.wait_connected(2)
        await asyncio.sleep(0.3)
        assert link.health.state is LinkState.CONNECTED and link.health.connections == 1
        assert link.health.last_error_code == "read_timeout"
        await link.stop()
        await asyncio.wait_for(task, 2)
        await srv.stop()
    run(go())


def test_settings_validation():
    for bad in [dict(port=0), dict(port=70000), dict(port=1, read_timeout=0), dict(port=1, inbound_queue_size=0)]:
        with pytest.raises(ValueError):
            TcpSettings(host="127.0.0.1", **bad)


def test_stream_close_is_idempotent():
    async def go():
        srv = await EchoServer().start()
        stream = await open_tcp(settings(srv.port), framer())
        await stream.close()
        await stream.close()
        with contextlib.suppress(Exception):
            await srv.stop()
    run(go())


def test_framed_stream_peer_reported():
    async def go():
        srv = await EchoServer().start()
        stream = await open_tcp(settings(srv.port), framer())
        assert stream.peer and stream.peer.startswith("127.0.0.1:")
        assert isinstance(stream, FramedStream)
        await stream.close()
        await srv.stop()
    run(go())
