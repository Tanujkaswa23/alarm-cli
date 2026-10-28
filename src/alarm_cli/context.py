from __future__ import annotations

from dataclasses import dataclass

from alarm_cli.storage import JsonStore


@dataclass
class Context:
    """Everything an action needs; every part is replaceable in tests."""

    console: object
    store: JsonStore
    clock: object
    player: object
    keys: object
