from datetime import date, datetime, time, timedelta

from alarm_cli.models import DAYS, WEEKDAYS, Alarm
from alarm_cli.scheduler import latest_due, next_trigger, pending, resolve_once_date, reschedule, revive

NOW = datetime(2026, 10, 28, 9, 0, 0).astimezone()  # Wednesday


def make(t, repeat=None, d=None, created=NOW, **kw):
    return Alarm(id="x", time=t, repeat=repeat or [], date=d, created_at=created.isoformat(), **kw)


def test_resolve_once_date():
    assert resolve_once_date(time(10, 0), NOW) == NOW.date()
    assert resolve_once_date(time(8, 0), NOW) == NOW.date() + timedelta(days=1)
    assert resolve_once_date(time(9, 0), NOW) == NOW.date() + timedelta(days=1)


def test_once_alarm_trigger():
    a = make(time(10, 0), d=NOW.date())
    assert next_trigger(a, NOW) == datetime(2026, 10, 28, 10, 0).astimezone()


def test_weekday_skips_weekend():
    friday_evening = datetime(2026, 10, 30, 20, 0).astimezone()
    a = make(time(7, 30), WEEKDAYS, created=friday_evening)
    nxt = next_trigger(a, friday_evening)
    assert nxt.date() == date(2026, 11, 2) and nxt.weekday() == 0


def test_month_and_year_rollover():
    ref = datetime(2026, 12, 31, 23, 0).astimezone()
    a = make(time(6, 0), list(DAYS), created=ref)
    assert next_trigger(a, ref).date() == date(2027, 1, 1)


def test_custom_days():
    a = make(time(9, 0), ["fri"])  # created Wed 09:00
    assert next_trigger(a, NOW).date() == date(2026, 10, 30)


def test_disabled_or_done_has_no_trigger():
    a = make(time(10, 0), d=NOW.date(), enabled=False)
    assert pending(a) is None
    b = make(time(10, 0), d=NOW.date(), state="done")
    assert next_trigger(b, NOW) is None


def test_latest_due_skips_old_occurrences():
    a = make(time(7, 0), list(DAYS), created=NOW - timedelta(days=10))
    due = latest_due(a, NOW)
    assert due.date() == NOW.date()  # today's 07:00, not ten stale ones
    assert latest_due(a, NOW - timedelta(hours=3)) is not None  # 06:00 yesterday-ish already due earlier days


def test_not_due_yet():
    a = make(time(10, 0), d=NOW.date())
    assert latest_due(a, NOW) is None
    assert latest_due(a, NOW + timedelta(hours=1)) is not None


def test_fired_once_alarm_is_not_due_again():
    a = make(time(10, 0), d=NOW.date())
    a.last_fired_at = datetime(2026, 10, 28, 10, 0).astimezone().isoformat()
    assert latest_due(a, NOW + timedelta(hours=5)) is None


def test_reschedule_and_revive():
    a = make(time(8, 0), d=NOW.date(), state="done", enabled=False)
    revive(a, NOW)  # 08:00 today already passed -> tomorrow
    assert a.enabled and a.state == "active" and a.date == NOW.date() + timedelta(days=1)
    b = make(time(10, 0), d=date(2026, 12, 25), state="done")
    revive(b, NOW)
    assert b.date == date(2026, 12, 25)  # future explicit date is kept
    c = make(time(8, 0))
    reschedule(c, NOW)
    assert c.date is not None
