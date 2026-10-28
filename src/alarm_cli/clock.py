import time
from datetime import datetime, timedelta


class SystemClock:
    def now(self) -> datetime:
        return datetime.now().astimezone()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class FakeClock:
    """Deterministic clock for tests: sleep() just advances time."""

    def __init__(self, start: datetime):
        self._now = start.astimezone()

    def now(self) -> datetime:
        return self._now

    def sleep(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)
