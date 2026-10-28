"""JSON file persistence (no database): alarms, settings, history."""
from __future__ import annotations

import json
import os
import secrets
import sys
from collections.abc import Callable
from pathlib import Path

from alarm_cli.models import Alarm, HistoryEvent, Settings

HISTORY_LIMIT = 100


def default_home() -> Path:
    env = os.environ.get("ALARM_CLI_HOME")
    if env:
        return Path(env)
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "alarm-cli"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "alarm-cli"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "alarm-cli"


def _warn_stderr(msg: str) -> None:
    print(f"Warning: {msg}", file=sys.stderr)


class JsonStore:
    def __init__(self, home: Path | None = None, warn: Callable[[str], None] = _warn_stderr):
        self.home = Path(home) if home else default_home()
        self.warn = warn
        self.alarms_path = self.home / "alarms.json"
        self.settings_path = self.home / "settings.json"
        self.history_path = self.home / "history.jsonl"

    # ---- low level ----
    def _write_atomic(self, path: Path, text: str) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)

    def _read_json(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("top-level value is not an object")
            return data
        except (ValueError, OSError) as exc:
            backup = path.with_name(path.name + ".bak")
            try:
                os.replace(path, backup)
                self.warn(f"{path.name} was unreadable ({exc}); saved as {backup.name}.")
            except OSError:
                self.warn(f"{path.name} is unreadable ({exc}).")
            return None

    # ---- alarms ----
    def alarms_mtime(self) -> int:
        try:
            return self.alarms_path.stat().st_mtime_ns
        except OSError:
            return 0

    def load_alarms(self) -> list[Alarm]:
        data = self._read_json(self.alarms_path)
        if not data:
            return []
        alarms = []
        for raw in data.get("alarms", []):
            try:
                alarms.append(Alarm.from_dict(raw))
            except (KeyError, ValueError, TypeError):
                self.warn(f"Skipped an invalid alarm entry: {raw!r}")
        return alarms

    def save_alarms(self, alarms: list[Alarm]) -> None:
        payload = {"version": 1, "alarms": [a.to_dict() for a in alarms]}
        self._write_atomic(self.alarms_path, json.dumps(payload, indent=2))

    def update_alarm(self, alarm_id: str, fn: Callable[[Alarm], None]) -> None:
        """Fresh load -> modify one alarm -> atomic save (avoids clobbering other edits)."""
        alarms = self.load_alarms()
        for a in alarms:
            if a.id == alarm_id:
                fn(a)
                self.save_alarms(alarms)
                return

    def new_id(self, existing: list[Alarm]) -> str:
        taken = {a.id for a in existing}
        while True:
            candidate = secrets.token_hex(3)
            if candidate not in taken:
                return candidate

    # ---- settings ----
    def load_settings(self) -> Settings:
        return Settings.from_dict(self._read_json(self.settings_path) or {})

    def save_settings(self, settings: Settings) -> None:
        self._write_atomic(self.settings_path, json.dumps(settings.to_dict(), indent=2))

    # ---- history ----
    def append_history(self, event: HistoryEvent) -> None:
        events = self.load_history()
        events.append(event)
        self._save_history(events[-HISTORY_LIMIT:])

    def load_history(self) -> list[HistoryEvent]:
        if not self.history_path.exists():
            return []
        events = []
        for line in self.history_path.read_text(encoding="utf-8").splitlines():
            try:
                events.append(HistoryEvent.from_dict(json.loads(line)))
            except (ValueError, KeyError, TypeError):
                continue
        return events

    def clear_history(self) -> None:
        self._save_history([])

    def _save_history(self, events: list[HistoryEvent]) -> None:
        text = "".join(json.dumps(e.to_dict()) + "\n" for e in events)
        self._write_atomic(self.history_path, text)
