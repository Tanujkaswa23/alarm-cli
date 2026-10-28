from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAYS = DAYS[:5]
WEEKENDS = DAYS[5:]


@dataclass
class Alarm:
    id: str
    time: time
    label: str = "Alarm"
    repeat: list[str] = field(default_factory=list)  # empty = one-time
    date: date | None = None  # used by one-time alarms and timers
    sound: str = "default"  # "default" | "silent" | path to .wav
    snooze_minutes: int = 5
    max_snoozes: int = 3  # 0 = unlimited
    enabled: bool = True
    kind: str = "alarm"  # "alarm" | "timer"
    created_at: str = ""
    last_fired_at: str | None = None
    state: str = "active"  # "active" | "done" | "missed"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "time": self.time.isoformat(),
            "date": self.date.isoformat() if self.date else None,
            "repeat": list(self.repeat),
            "label": self.label,
            "sound": self.sound,
            "snooze_minutes": self.snooze_minutes,
            "max_snoozes": self.max_snoozes,
            "enabled": self.enabled,
            "kind": self.kind,
            "created_at": self.created_at,
            "last_fired_at": self.last_fired_at,
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Alarm:
        return cls(
            id=str(d["id"]),
            time=time.fromisoformat(d["time"]),
            date=date.fromisoformat(d["date"]) if d.get("date") else None,
            repeat=[x for x in d.get("repeat", []) if x in DAYS],
            label=str(d.get("label", "Alarm")),
            sound=str(d.get("sound", "default")),
            snooze_minutes=int(d.get("snooze_minutes", 5)),
            max_snoozes=int(d.get("max_snoozes", 3)),
            enabled=bool(d.get("enabled", True)),
            kind=str(d.get("kind", "alarm")),
            created_at=str(d["created_at"]),
            last_fired_at=d.get("last_fired_at"),
            state=str(d.get("state", "active")),
        )


@dataclass
class Settings:
    snooze_minutes: int = 5
    auto_stop_seconds: int = 60
    grace_minutes: int = 5
    default_sound: str = "beep"  # "beep" | path to .wav
    time_format: str = "24h"  # "24h" | "12h"

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> Settings:
        s = cls()
        for key, default in list(s.__dict__.items()):
            value = d.get(key, default)
            if isinstance(value, type(default)) and not isinstance(value, bool):
                setattr(s, key, value)
        if s.time_format not in ("24h", "12h"):
            s.time_format = "24h"
        return s


@dataclass
class HistoryEvent:
    ts: str
    alarm_id: str
    label: str
    event: str  # fired | snoozed | dismissed | missed

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> HistoryEvent:
        return cls(d["ts"], d["alarm_id"], d["label"], d["event"])
