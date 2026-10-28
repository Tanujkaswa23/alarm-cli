"""Non-blocking single-key reader (used by ring mode and the live clock)."""
from __future__ import annotations

import sys

try:
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None  # type: ignore[assignment]
    import select
    import termios
    import tty


class KeyReader:
    """poll() returns a lowercase character (Enter -> '\\r') or None. Use as a context manager."""

    def __init__(self) -> None:
        self._old_attrs = None

    def __enter__(self) -> KeyReader:
        if msvcrt is None and sys.stdin.isatty():
            fd = sys.stdin.fileno()
            self._old_attrs = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._old_attrs is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_attrs)
            self._old_attrs = None

    def poll(self) -> str | None:
        if msvcrt is not None:
            if not msvcrt.kbhit():
                return None
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):  # special key, swallow its second code
                msvcrt.getwch()
                return None
            return "\r" if ch == "\n" else ch.lower()
        if not sys.stdin.isatty():
            return None
        if select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            return "\r" if ch == "\n" else ch.lower()
        return None


class FakeKeys:
    """Scripted keys: each poll() pops one entry; None means 'no key pressed'."""

    def __init__(self, script: list[str | None] | None = None):
        self.script = list(script or [])

    def __enter__(self) -> FakeKeys:
        return self

    def __exit__(self, *exc: object) -> None:
        pass

    def poll(self) -> str | None:
        return self.script.pop(0) if self.script else None
