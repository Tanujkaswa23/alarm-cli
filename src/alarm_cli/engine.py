"""Ring mode: watch the clock, ring due alarms, handle snooze / dismiss / auto-stop."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from alarm_cli.context import Context
from alarm_cli.models import Alarm, HistoryEvent, Settings
from alarm_cli.parsing import format_countdown, format_time
from alarm_cli.render import next_alarm
from alarm_cli.scheduler import latest_due

TICK = 0.5
RING_TICK = 0.2


@dataclass
class Due:
    alarm: Alarm
    when: datetime


def resolve_sound(alarm: Alarm, settings: Settings) -> str:
    return settings.default_sound if alarm.sound == "default" else alarm.sound


class Engine:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self._alarms: list[Alarm] = []
        self._mtime: int | None = None

    # ---- data ----
    def alarms(self) -> list[Alarm]:
        """Cached alarm list, reloaded when the file changes on disk (e.g. edited in another terminal)."""
        mtime = self.ctx.store.alarms_mtime()
        if mtime != self._mtime:
            self._alarms = self.ctx.store.load_alarms()
            self._mtime = mtime
        return self._alarms

    def _log(self, alarm: Alarm, event: str) -> None:
        self.ctx.store.append_history(
            HistoryEvent(self.ctx.clock.now().isoformat(timespec="seconds"), alarm.id, alarm.label, event)
        )

    def _finish(self, due: Due, outcome: str) -> None:
        """Persist the result of one occurrence. outcome: 'dismissed' or 'missed'."""

        def apply(a: Alarm) -> None:
            a.last_fired_at = due.when.isoformat()
            if not a.repeat:  # one-time alarms and timers are finished after their only occurrence
                a.state = "done" if outcome == "dismissed" else "missed"
                a.enabled = False

        self.ctx.store.update_alarm(due.alarm.id, apply)
        self._log(due.alarm, outcome)

    # ---- detection ----
    def collect_due(self, now: datetime) -> list[Due]:
        due: list[Due] = []
        grace = None
        for a in self.alarms():
            when = latest_due(a, now)
            if when is None:
                continue
            if grace is None:
                grace = timedelta(minutes=self.ctx.store.load_settings().grace_minutes)
            if now - when <= grace:
                due.append(Due(a, when))
            else:
                self._finish(Due(a, when), "missed")
        return due

    # ---- ringing ----
    def ring(self, due: list[Due]) -> None:
        ctx, c = self.ctx, self.ctx.console
        settings = ctx.store.load_settings()
        sounds = [resolve_sound(d.alarm, settings) for d in due]
        sound = next((s for s in sounds if s != "silent"), "silent")
        snooze_minutes = min(d.alarm.snooze_minutes for d in due)
        limits = [d.alarm.max_snoozes for d in due if d.alarm.max_snoozes > 0]
        max_snoozes = min(limits) if limits else None  # None = unlimited
        fmt = settings.time_format

        c.print("")
        for d in due:
            c.print(f" *** ALARM {format_time(d.alarm.time, fmt)} - {d.alarm.label} ***")
            self._log(d.alarm, "fired")

        snoozes = 0
        outcome = "dismissed"
        ctx.player.play(sound)
        started = ctx.clock.now()
        try:
            while True:
                key = ctx.keys.poll()
                now = ctx.clock.now()
                if key in ("d", "\r"):
                    break
                if key == "s":
                    if max_snoozes is None or snoozes < max_snoozes:
                        snoozes += 1
                        ctx.player.stop()
                        for d in due:
                            self._log(d.alarm, "snoozed")
                        if not self._wait_snooze(snooze_minutes):
                            break  # dismissed during snooze
                        ctx.player.play(sound)
                        started = ctx.clock.now()
                        continue
                    c.print(" No snoozes left.")
                if (now - started).total_seconds() >= settings.auto_stop_seconds:
                    outcome = "missed"
                    c.print(" Not acknowledged - alarm stopped and marked missed.")
                    break
                left = "unlimited" if max_snoozes is None else str(max_snoozes - snoozes)
                c.status(f" [s] snooze {snooze_minutes}m ({left} left)   [d] dismiss")
                ctx.clock.sleep(RING_TICK)
        finally:
            ctx.player.stop()
            c.clear_status()
            for d in due:
                self._finish(d, outcome)
        c.print(" Alarm dismissed." if outcome == "dismissed" else "")

    def _wait_snooze(self, minutes: int) -> bool:
        """Wait out a snooze. Returns False if the user dismissed instead."""
        ctx = self.ctx
        until = ctx.clock.now() + timedelta(minutes=minutes)
        while True:
            now = ctx.clock.now()
            if now >= until:
                ctx.console.clear_status()
                return True
            key = ctx.keys.poll()
            if key in ("d", "\r"):
                return False
            ctx.console.status(f" Snoozed - ringing again in {format_countdown(until - now)}   [d] dismiss")
            ctx.clock.sleep(TICK)

    # ---- main loop ----
    def run(self) -> None:
        """Ring mode. Returns when the user presses `m`."""
        ctx, c = self.ctx, self.ctx.console
        settings = ctx.store.load_settings()
        active = sum(1 for a in self.alarms() if a.enabled and a.state == "active")
        c.print(f" Ring mode - watching {active} alarm(s).   [m] back to menu   [Ctrl+C] back to menu")
        with ctx.keys:
            while True:
                now = ctx.clock.now()
                due = self.collect_due(now)
                if due:
                    c.clear_status()
                    self.ring(due)
                    continue
                nxt = next_alarm(self.alarms(), now)
                if nxt:
                    a, when = nxt
                    c.status(f" Next: {a.label} at {format_time(when.timetz().replace(tzinfo=None), settings.time_format)}"
                             f" (in {format_countdown(when - now)})   [m] menu")
                else:
                    c.status(" No active alarms.   [m] menu")
                if ctx.keys.poll() == "m":
                    c.clear_status()
                    return
                ctx.clock.sleep(TICK)
