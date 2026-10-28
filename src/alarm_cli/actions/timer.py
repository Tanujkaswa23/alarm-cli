"""Menu item 6: countdown timer (stored as a one-time alarm)."""
from __future__ import annotations

from alarm_cli import prompts
from alarm_cli.context import Context
from alarm_cli.models import Alarm
from alarm_cli.parsing import format_time


def set_timer(ctx: Context) -> None:
    c = ctx.console
    settings = ctx.store.load_settings()
    duration = prompts.ask_duration(c, "Duration (e.g. 90s, 10m, 1h30m, 00:05:00)")
    label = prompts.ask_text(c, "Label", "Timer")
    now = ctx.clock.now()
    due = now + duration
    alarms = ctx.store.load_alarms()
    alarms.append(
        Alarm(
            id=ctx.store.new_id(alarms), time=due.timetz().replace(tzinfo=None, microsecond=0), label=label,
            date=due.date(), snooze_minutes=settings.snooze_minutes, kind="timer", created_at=now.isoformat(),
        )
    )
    ctx.store.save_alarms(alarms)
    c.print(f"Timer set - rings at {format_time(due.timetz().replace(tzinfo=None, microsecond=0), settings.time_format)}. "
            "Start ring mode (option 7) to hear it.")
