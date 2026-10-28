from datetime import datetime, time, timedelta

from alarm_cli.engine import Engine
from alarm_cli.models import DAYS, Alarm
from alarm_cli.scheduler import next_trigger

from conftest import START


def alarm(id_="a1", t=time(9, 1), repeat=None, date=None, created=START, **kw):
    return Alarm(
        id=id_, time=t, label=f"alarm-{id_}", repeat=repeat or [], date=date if repeat else (date or START.date()),
        created_at=created.isoformat(), **kw,
    )


class ReactiveKeys:
    """Keys that react to what the engine is doing: policy(player, store) -> key."""

    def __init__(self, ctx, policy):
        self.ctx, self.policy = ctx, policy

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def poll(self):
        return self.policy(self.ctx)


def events(ctx):
    return [(e.alarm_id, e.event) for e in ctx.store.load_history()]


def run_until_menu(ctx, ring_key):
    """Press `ring_key` while ringing, `m` once nothing is left to do."""

    def policy(c):
        if c.player.playing:
            return ring_key(c)
        return "m" if all(not a.enabled or a.state != "active" or a.repeat for a in c.store.load_alarms()) \
            and any(e.event in ("dismissed", "missed") for e in c.store.load_history()) else None

    ctx.keys = ReactiveKeys(ctx, policy)
    Engine(ctx).run()


def test_ring_and_dismiss_one_time(ctx):
    ctx.store.save_alarms([alarm()])
    run_until_menu(ctx, lambda c: "d")
    a = ctx.store.load_alarms()[0]
    assert a.state == "done" and not a.enabled
    assert events(ctx) == [("a1", "fired"), ("a1", "dismissed")]
    assert ctx.player.calls == ["play:beep", "stop"]
    assert ctx.clock.now() >= START + timedelta(minutes=1)


def test_snooze_rings_again(ctx):
    ctx.store.save_alarms([alarm(snooze_minutes=5)])
    presses = []

    def key(c):
        if not presses:
            presses.append("s")
            return "s"
        return "d"

    run_until_menu(ctx, key)
    assert events(ctx) == [("a1", "fired"), ("a1", "snoozed"), ("a1", "dismissed")]
    assert ctx.player.calls == ["play:beep", "stop", "play:beep", "stop"]
    assert ctx.clock.now() >= START + timedelta(minutes=6)  # 09:01 due + 5 min snooze


def test_max_snoozes_then_auto_stop_marks_missed(ctx):
    ctx.store.save_alarms([alarm(max_snoozes=1, snooze_minutes=1)])
    run_until_menu(ctx, lambda c: "s")
    assert "No snoozes left" in ctx.console.text
    assert ctx.store.load_alarms()[0].state == "missed"
    assert ("a1", "missed") in events(ctx)


def test_auto_stop_without_keypress(ctx):
    ctx.store.save_alarms([alarm()])
    run_until_menu(ctx, lambda c: None)
    assert ctx.store.load_alarms()[0].state == "missed"
    assert not ctx.player.playing


def test_dismiss_during_snooze(ctx):
    ctx.store.save_alarms([alarm(snooze_minutes=5)])
    state = {"snoozed": False}

    def policy(c):
        if c.player.playing and not state["snoozed"]:
            state["snoozed"] = True
            return "s"
        if not c.player.playing and state["snoozed"] and not any(e.event == "dismissed" for e in c.store.load_history()):
            return "d"
        return "m" if any(e.event == "dismissed" for e in c.store.load_history()) else None

    ctx.keys = ReactiveKeys(ctx, policy)
    Engine(ctx).run()
    assert events(ctx)[-1] == ("a1", "dismissed")
    assert ctx.player.calls == ["play:beep", "stop"]


def test_recurring_alarm_stays_active(ctx):
    ctx.store.save_alarms([alarm(repeat=list(DAYS))])
    run_until_menu(ctx, lambda c: "d")
    a = ctx.store.load_alarms()[0]
    assert a.enabled and a.state == "active" and a.last_fired_at
    nxt = next_trigger(a, ctx.clock.now())
    assert nxt.date() == START.date() + timedelta(days=1)


def test_simultaneous_alarms_ring_together(ctx):
    ctx.store.save_alarms([alarm("a1"), alarm("b2")])
    run_until_menu(ctx, lambda c: "d")
    assert ctx.player.calls.count("play:beep") == 1
    assert {i for i, e in events(ctx) if e == "dismissed"} == {"a1", "b2"}


def test_late_start_outside_grace_is_missed_not_rung(make_ctx):
    now = START  # 09:00; alarm daily at 07:00 created 2 days ago
    ctx = make_ctx(start=now)
    ctx.store.save_alarms([alarm(t=time(7, 0), repeat=list(DAYS), created=now - timedelta(days=2))])
    engine = Engine(ctx)
    assert engine.collect_due(now) == []
    assert events(ctx) == [("a1", "missed")]  # one entry, not one per skipped day
    assert ctx.store.load_alarms()[0].state == "active"
    assert engine.collect_due(now) == []  # not reported twice


def test_late_start_inside_grace_rings(ctx):
    ctx.store.save_alarms([alarm(t=time(8, 58), created=START - timedelta(days=1), date=START.date())])
    due = Engine(ctx).collect_due(START)
    assert [d.alarm.id for d in due] == ["a1"]


def test_hot_reload_picks_up_changes(ctx):
    engine = Engine(ctx)
    assert engine.alarms() == []
    ctx.store.save_alarms([alarm()])
    assert [a.id for a in engine.alarms()] == ["a1"]


def test_silent_alarm_uses_silent_sound(ctx):
    ctx.store.save_alarms([alarm(sound="silent")])
    run_until_menu(ctx, lambda c: "d")
    assert ctx.player.calls[0] == "play:silent"


def test_ring_mode_exits_on_m(ctx):
    ctx.keys = ReactiveKeys(ctx, lambda c: "m")
    Engine(ctx).run()
    assert "No active alarms" in ctx.console.text
