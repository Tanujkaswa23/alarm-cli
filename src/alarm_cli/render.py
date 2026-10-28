"""Text rendering: header, alarm table."""
from __future__ import annotations

from datetime import datetime

from alarm_cli.models import Alarm, Settings
from alarm_cli.parsing import describe_repeat, format_remaining, format_time
from alarm_cli.scheduler import next_trigger

WIDTH = 60


def state_label(a: Alarm) -> str:
    if a.state == "done":
        return "Done"
    if a.state == "missed":
        return "Missed"
    return "Enabled" if a.enabled else "Disabled"


def sorted_alarms(alarms: list[Alarm], now: datetime) -> list[Alarm]:
    """Active alarms by next trigger, then the rest by clock time."""

    def key(a: Alarm):
        nxt = next_trigger(a, now)
        return (nxt is None, nxt.timestamp() if nxt else 0, a.time)

    return sorted(alarms, key=key)


def next_alarm(alarms: list[Alarm], now: datetime) -> tuple[Alarm, datetime] | None:
    best = None
    for a in alarms:
        nxt = next_trigger(a, now)
        if nxt and (best is None or nxt < best[1]):
            best = (a, nxt)
    return best


def describe_next(alarm: Alarm, when: datetime, now: datetime, settings: Settings) -> str:
    stamp = when.strftime("%a %d %b ") + format_time(when.timetz().replace(tzinfo=None), settings.time_format)
    return f'"{alarm.label}" at {stamp} (in {format_remaining(when - now)})'


def alarm_table(alarms: list[Alarm], now: datetime, settings: Settings, numbered: bool = True) -> list[str]:
    fmt = settings.time_format
    rows = []
    for i, a in enumerate(alarms, 1):
        nxt = next_trigger(a, now)
        nxt_s = "-"
        if nxt:
            nxt_s = f"{nxt.strftime('%a %d %b')} {format_time(nxt.timetz().replace(tzinfo=None), fmt)} (in {format_remaining(nxt - now)})"
        rows.append(
            (
                str(i),
                a.id,
                format_time(a.time, fmt),
                a.label if a.kind == "alarm" else f"[timer] {a.label}",
                describe_repeat(a.repeat),
                state_label(a),
                nxt_s,
            )
        )
    headers = ("No.", "ID", "Time", "Label", "Repeat", "State", "Next")
    widths = [max([len(h), *(len(r[c]) for r in rows)]) for c, h in enumerate(headers)]
    lines = ["  ".join(h.ljust(w) for h, w in zip(headers, widths))]
    lines.append("  ".join("-" * w for w in widths))
    lines += ["  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows]
    return lines


def header(alarms: list[Alarm], now: datetime, settings: Settings) -> list[str]:
    fmt = "%a %d %b %Y  " + ("%H:%M:%S" if settings.time_format == "24h" else "%I:%M:%S %p")
    active = [a for a in alarms if a.enabled and a.state == "active"]
    nxt = next_alarm(alarms, now)
    lines = [
        " CLI ALARM CLOCK ".center(WIDTH, "="),
        f" Now: {now.strftime(fmt)}     Active alarms: {len(active)}",
        " Next: " + (describe_next(*nxt, now, settings) if nxt else "none scheduled"),
        " (Alarms only ring while Ring mode is running - option 7)",
        "-" * WIDTH,
    ]
    return lines
