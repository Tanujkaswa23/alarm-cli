"""Reusable field prompts shared by Add and Edit (current value = default)."""
from __future__ import annotations

from datetime import date, datetime, time

from alarm_cli import prompts
from alarm_cli.context import Context
from alarm_cli.errors import ValidationError
from alarm_cli.models import DAYS, WEEKDAYS, WEEKENDS
from alarm_cli.scheduler import _local

REPEAT_OPTIONS = ["Once", "Every day", "Weekdays (Mon-Fri)", "Weekends", "Custom days"]
SOUND_OPTIONS = ["Default sound (from settings)", "Custom .wav file", "Silent (visual only)"]


def ask_alarm_time(ctx: Context, current: time | None = None) -> time:
    fmt = ctx.store.load_settings().time_format
    return prompts.ask_time(ctx.console, "Time (HH:MM or h:MM AM/PM)", current, fmt)


def ask_label(ctx: Context, current: str = "Alarm") -> str:
    return prompts.ask_text(ctx.console, "Label", current)


def _repeat_index(repeat: list[str]) -> int:
    if not repeat:
        return 1
    if len(repeat) == 7:
        return 2
    if repeat == WEEKDAYS:
        return 3
    if repeat == WEEKENDS:
        return 4
    return 5


def ask_repeat(
    ctx: Context,
    at: time,
    now: datetime,
    current_repeat: list[str] | None = None,
    current_date: date | None = None,
) -> tuple[list[str], date | None]:
    """Returns (repeat days, explicit date). Empty repeat = one-time."""
    c = ctx.console
    idx = prompts.ask_choice(c, REPEAT_OPTIONS, "Repeat:", default=_repeat_index(current_repeat or []))
    if idx == 0:

        def not_past(d: date) -> None:
            if _local(d, at) <= now:
                raise ValidationError("That date and time is already in the past.")

        d = prompts.ask_optional_date(c, "Date (YYYY-MM-DD)", current_date, not_past)
        return [], d
    if idx == 1:
        return list(DAYS), None
    if idx == 2:
        return list(WEEKDAYS), None
    if idx == 3:
        return list(WEEKENDS), None
    return prompts.ask_days(c), None


def ask_sound(ctx: Context, current: str = "default") -> str:
    c = ctx.console
    default = {"default": 1, "silent": 3}.get(current, 2)
    idx = prompts.ask_choice(c, SOUND_OPTIONS, "Sound:", default=default)
    if idx == 0:
        return "default"
    if idx == 2:
        return "silent"
    return prompts.ask_wav_path(c)


def ask_snooze(ctx: Context, current: int) -> int:
    return prompts.ask_int(ctx.console, "Snooze minutes", 1, 60, current)


def ask_max_snoozes(ctx: Context, current: int) -> int:
    return prompts.ask_int(ctx.console, "Max snoozes (0 = unlimited)", 0, 20, current)


def sound_label(sound: str) -> str:
    return {"default": "default", "silent": "silent"}.get(sound, sound)
