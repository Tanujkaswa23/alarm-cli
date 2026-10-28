"""Pure scheduling logic: when does an alarm fire next?"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from alarm_cli.models import DAYS, Alarm


def _local(d: date, t: time) -> datetime:
    return datetime.combine(d, t).astimezone()  # naive -> local tz-aware


def resolve_once_date(t: time, now: datetime) -> date:
    """Today if the time is still ahead, otherwise tomorrow."""
    now = now.astimezone()
    return now.date() if _local(now.date(), t) > now else now.date() + timedelta(days=1)


def occurrence_after(alarm: Alarm, ref: datetime) -> datetime | None:
    """First scheduled occurrence strictly after `ref`."""
    ref = ref.astimezone()
    if not alarm.repeat:
        if alarm.date is None:
            return None
        dt = _local(alarm.date, alarm.time)
        return dt if dt > ref else None
    for i in range(8):
        d = ref.date() + timedelta(days=i)
        if DAYS[d.weekday()] in alarm.repeat:
            dt = _local(d, alarm.time)
            if dt > ref:
                return dt
    return None


def pending(alarm: Alarm) -> datetime | None:
    """Next occurrence that has not fired yet (may be in the past)."""
    if not alarm.enabled or alarm.state != "active":
        return None
    ref = datetime.fromisoformat(alarm.last_fired_at or alarm.created_at)
    return occurrence_after(alarm, ref)


def next_trigger(alarm: Alarm, now: datetime) -> datetime | None:
    """Upcoming trigger for display; None if none is coming."""
    p = pending(alarm)
    if p is None or p >= now:
        return p
    return occurrence_after(alarm, now) if alarm.repeat else None


def latest_due(alarm: Alarm, now: datetime) -> datetime | None:
    """Most recent unfired occurrence at or before `now`; older ones are skipped."""
    p = pending(alarm)
    if p is None or p > now:
        return None
    while True:
        nxt = occurrence_after(alarm, p)
        if nxt is not None and nxt <= now:
            p = nxt
        else:
            return p


def reschedule(alarm: Alarm, now: datetime) -> None:
    """Reset firing state after the schedule of an alarm changed."""
    alarm.created_at = now.isoformat()
    alarm.last_fired_at = None
    alarm.state = "active"
    if not alarm.repeat and alarm.date is None:
        alarm.date = resolve_once_date(alarm.time, now)


def revive(alarm: Alarm, now: datetime) -> None:
    """Re-enable an alarm so its next occurrence is measured from now."""
    if not alarm.repeat and (alarm.date is None or _local(alarm.date, alarm.time) <= now):
        alarm.date = None  # stale: pick the next occurrence of the time
    alarm.enabled = True
    reschedule(alarm, now)
