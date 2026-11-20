"""Stream framing, separated from record parsing.

A TCP stream has no message boundaries; a `Framer` turns arbitrary chunks
(partial reads, several messages per read) into whole frames and back.

There is NO default framing. `DelimitedFramer` needs its start/end markers
passed explicitly, because the FIAS framing rules are not verified (HF-06).
The provisional markers used by tests and the simulator are declared in
`app/integrations/simulators/fixtures.py` and labelled as a test assumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.integrations.core.errors import FrameTooLarge, ProtocolError


class Framer(Protocol):
    def feed(self, data: bytes) -> list[bytes]: ...
    def frame(self, payload: bytes) -> bytes: ...
    def reset(self) -> None: ...
    def take_errors(self) -> list[ProtocolError]: ...
    @property
    def buffered(self) -> int: ...


@dataclass
class FramerStats:
    frames: int = 0
    discarded_bytes: int = 0
    resyncs: int = 0
    oversized: int = 0


@dataclass
class DelimitedFramer:
    """Frames delimited by an optional start marker and a mandatory end marker.

    * Bytes before a start marker are discarded (counted, never logged).
    * A second start marker before the end marker means the previous frame
      was truncated: the partial frame is dropped and parsing resynchronises.
    * A frame (or an unterminated buffer) larger than `max_frame_bytes` is
      dropped and the buffer cleared, so one bad peer cannot grow memory
      without bound. The error is NOT raised mid-feed (that would lose the
      valid frames already extracted from the same chunk); it is queued and
      returned by `take_errors()`.
    * Payload bytes equal to a marker cannot be represented; `frame()` refuses
      them rather than emitting an ambiguous stream.
    """

    end: bytes
    start: bytes | None = None
    max_frame_bytes: int = 64 * 1024
    stats: FramerStats = field(default_factory=FramerStats)
    _buf: bytearray = field(default_factory=bytearray, repr=False)
    _errors: list = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self.end:
            raise ValueError("end marker is required")
        if self.start is not None and not self.start:
            raise ValueError("start marker, when given, must be non-empty")
        if self.max_frame_bytes < 1:
            raise ValueError("max_frame_bytes must be positive")

    @property
    def buffered(self) -> int:
        return len(self._buf)

    def reset(self) -> None:
        self._buf.clear()

    def take_errors(self) -> list[ProtocolError]:
        errors, self._errors = self._errors, []
        return errors

    def frame(self, payload: bytes) -> bytes:
        if len(payload) > self.max_frame_bytes:
            raise FrameTooLarge("Outbound payload exceeds the frame size limit.")
        if self.end in payload or (self.start and self.start in payload):
            raise ProtocolError("Payload contains a framing marker.", code="payload_contains_marker")
        return (self.start or b"") + payload + self.end

    def feed(self, data: bytes) -> list[bytes]:
        self._buf.extend(data)
        frames: list[bytes] = []
        while True:
            if self.start is not None:
                idx = self._buf.find(self.start)
                if idx < 0:
                    # Keep a possible partial start marker at the tail.
                    keep = len(self.start) - 1
                    drop = len(self._buf) - keep if len(self._buf) > keep else 0
                    if drop:
                        self.stats.discarded_bytes += drop
                        del self._buf[:drop]
                    break
                if idx > 0:
                    self.stats.discarded_bytes += idx
                    del self._buf[:idx]
                body_start = len(self.start)
            else:
                body_start = 0

            end_idx = self._buf.find(self.end, body_start)
            if self.start is not None:
                restart = self._buf.find(self.start, body_start)
                if restart >= 0 and (end_idx < 0 or restart < end_idx):
                    self.stats.resyncs += 1
                    self.stats.discarded_bytes += restart
                    del self._buf[:restart]
                    continue
            if end_idx < 0:
                if len(self._buf) - body_start > self.max_frame_bytes:
                    self.stats.oversized += 1
                    self._buf.clear()
                    self._errors.append(FrameTooLarge("Unterminated frame exceeds the frame size limit."))
                break
            payload = bytes(self._buf[body_start:end_idx])
            del self._buf[: end_idx + len(self.end)]
            if len(payload) > self.max_frame_bytes:
                self.stats.oversized += 1
                self._errors.append(FrameTooLarge("Frame exceeds the frame size limit."))
                continue
            self.stats.frames += 1
            frames.append(payload)
        return frames
