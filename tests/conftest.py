from datetime import datetime

import pytest

from alarm_cli.clock import FakeClock
from alarm_cli.console import FakeConsole
from alarm_cli.context import Context
from alarm_cli.keys import FakeKeys
from alarm_cli.ringer import FakePlayer
from alarm_cli.storage import JsonStore

START = datetime(2026, 10, 28, 9, 0, 0).astimezone()  # a Wednesday


@pytest.fixture
def make_ctx(tmp_path):
    def factory(inputs=None, keys=None, start=START):
        warnings: list[str] = []
        return Context(
            console=FakeConsole(inputs),
            store=JsonStore(tmp_path, warn=warnings.append),
            clock=FakeClock(start),
            player=FakePlayer(),
            keys=FakeKeys(keys),
        )

    return factory


@pytest.fixture
def ctx(make_ctx):
    return make_ctx()
