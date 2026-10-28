"""Pure parsing/formatting helpers for user input."""
from __future__ import annotations

import re
from datetime import date, time, timedelta

from alarm_cli.errors import ValidationError
from alarm_cli.models import DAYS, WEEKDAYS, WEEKENDS

_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?\s*([ap]m)?")
_DURATION_RE = re.compile(r"(?:\d+\s*[hms]\s*)+")
_DURATION_PART = re.compile(r"(\d+)\s*([hms])")
_CLOCK_DURATION_RE = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})")

_DAY_ALIASES = {d: d for d in DAYS}
_DAY_ALIASES.update(
    {
        "monday": "mon", "tuesday": "tue", "tues": "tue", "wednesday": "wed",
        "thursday": "thu", "thur": "thu", "thurs": "thu", "friday": "fri",
        "saturday": "sat", "sunday": "sun",
    }
)


def parse_time(text: str) -> time:
    msg = "Invalid time. Use HH:MM (24h) or h:MM AM/PM, e.g. 07:30 or 7:30 PM."
    m = _TIME_RE.fullmatch(text.strip().lower())
    if not m:
        raise ValidationError(msg)
    hour, minute, second, meridiem = m.groups()
    if minute is None and meridiem is None:
        raise ValidationError(msg)
    h, mi, s = int(hour), int(minute or 0), int(second or 0)
    if meridiem:
        if not 1 <= h <= 12:
            raise ValidationError(msg)
        h = h % 12 + (12 if meridiem == "pm" else 0)
    if h > 23 or mi > 59 or s > 59:
        raise ValidationError(msg)
    return time(h, mi, s)


def parse_duration(text: str) -> timedelta:
    msg = "Invalid duration. Use e.g. 90s, 10m, 1h30m, 00:05:00 (a bare number means minutes)."
    t = text.strip().lower()
    if t.isdigit():
        total = int(t) * 60
    elif m := _CLOCK_DURATION_RE.fullmatch(t):
        h, mi, s = map(int, m.groups())
        if mi > 59 or s > 59:
            raise ValidationError(msg)
        total = h * 3600 + mi * 60 + s
    elif _DURATION_RE.fullmatch(t):
        mult = {"h": 3600, "m": 60, "s": 1}
        total = sum(int(n) * mult[u] for n, u in _DURATION_PART.findall(t))
    else:
        raise ValidationError(msg)
    if total <= 0:
        raise ValidationError("Duration must be greater than zero.")
    if total > 24 * 3600:
        raise ValidationError("Duration can be at most 24 hours.")
    return timedelta(seconds=total)


def parse_days(text: str) -> list[str]:
    tokens = [t for t in re.split(r"[,\s]+", text.strip().lower()) if t]
    if not tokens:
        raise ValidationError("Enter at least one day, e.g. mon,wed,fri.")
    days = set()
    for tok in tokens:
        if tok not in _DAY_ALIASES:
            raise ValidationError(f"Unknown day '{tok}'. Use mon,tue,wed,thu,fri,sat,sun.")
        days.add(_DAY_ALIASES[tok])
    return [d for d in DAYS if d in days]


def parse_date(text: str) -> date:
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        raise ValidationError("Invalid date. Use YYYY-MM-DD, e.g. 2026-12-25.") from None


def format_time(t: time, fmt: str = "24h") -> str:
    if fmt == "12h":
        return t.strftime("%I:%M:%S %p" if t.second else "%I:%M %p").lstrip("0")
    return t.strftime("%H:%M:%S" if t.second else "%H:%M")


def format_remaining(delta: timedelta) -> str:
    total = max(int(delta.total_seconds()), 0)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def format_countdown(delta: timedelta) -> str:
    total = max(int(delta.total_seconds()), 0)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def describe_repeat(repeat: list[str]) -> str:
    if not repeat:
        return "Once"
    if len(repeat) == 7:
        return "Daily"
    if repeat == WEEKDAYS:
        return "Weekdays"
    if repeat == WEEKENDS:
        return "Weekends"
    return ",".join(d.capitalize() for d in repeat)
