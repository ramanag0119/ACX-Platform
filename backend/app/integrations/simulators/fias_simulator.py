"""Local TCP test simulator speaking the PROVISIONAL TEST record set.

Guards (all enforced in `start()`):
* INTEGRATION_SIMULATOR_ENABLED must be true (explicit opt-in);
* the bind address must be a loopback address;
* it is never started by the API: app.main does not import this package.

It does not pretend to be a real PMS: it only frames and sends the synthetic
records from `fixtures.py` and records what it receives.

Manual run (development only):
    INTEGRATION_SIMULATOR_ENABLED=true python -m app.integrations.simulators.fias_simulator --port 5010
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import ipaddress
import logging

from app.integrations.config import get_integration_settings
from app.integrations.core.errors import TransportError
from app.integrations.simulators.fixtures import provisional_test_framer
from app.integrations.transport.tcp import FramedStream

logger = logging.getLogger("hms.integrations.simulator")


class SimulatorDisabled(RuntimeError):
    pass


def _assert_loopback(host: str) -> None:
    try:
        ok = ipaddress.ip_address(host).is_loopback
    except ValueError:
        ok = host == "localhost"
    if not ok:
        raise SimulatorDisabled("The simulator binds to loopback addresses only.")


class FiasTestSimulator:
    def __init__(self, host: str = "127.0.0.1", port: int = 0, *, enabled: bool | None = None) -> None:
        self.host = host
        self.port = port
        self._enabled = get_integration_settings().SIMULATOR_ENABLED if enabled is None else enabled
        self._server: asyncio.base_events.Server | None = None
        self._streams: list[FramedStream] = []
        self.received: list[bytes] = []
        self._connected = asyncio.Event()

    async def start(self) -> int:
        if not self._enabled:
            raise SimulatorDisabled("Set INTEGRATION_SIMULATOR_ENABLED=true to run the test simulator.")
        _assert_loopback(self.host)
        self._server = await asyncio.start_server(self._on_client, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]
        logger.info("TEST simulator listening on %s:%s", self.host, self.port)
        return self.port

    async def _on_client(self, reader, writer) -> None:
        stream = FramedStream(reader, writer, provisional_test_framer(), read_timeout=3600, write_timeout=5)
        self._streams.append(stream)
        self._connected.set()
        try:
            while True:
                self.received.append(await stream.receive())
        except TransportError:
            pass
        finally:
            await stream.close()

    async def wait_for_client(self, timeout: float = 5.0) -> None:
        await asyncio.wait_for(self._connected.wait(), timeout)

    async def send_record(self, record: bytes) -> None:
        if not self._streams:
            raise RuntimeError("no client connected")
        await self._streams[-1].send(record)

    async def send_raw(self, data: bytes) -> None:
        """Bypass framing, e.g. to test partial / malformed streams."""
        if not self._streams:
            raise RuntimeError("no client connected")
        stream = self._streams[-1]
        stream._writer.write(data)  # noqa: SLF001 - test-only raw access
        await stream._writer.drain()  # noqa: SLF001

    async def drop_clients(self) -> None:
        for stream in self._streams:
            await stream.close()
        self._streams.clear()
        self._connected.clear()

    async def stop(self) -> None:
        await self.drop_clients()
        if self._server is not None:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()
            self._server = None


async def _main(port: int) -> None:  # pragma: no cover - manual tool
    sim = FiasTestSimulator(port=port)
    await sim.start()
    await asyncio.Event().wait()


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(description="ACX TEST-ONLY FIAS-style simulator")
    parser.add_argument("--port", type=int, default=0)
    asyncio.run(_main(parser.parse_args().port))
