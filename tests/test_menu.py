from datetime import timedelta

from alarm_cli.app import run_menu


def run(ctx):
    code = run_menu(ctx)
    assert code == 0
    return ctx.console.text


def test_add_weekday_alarm(make_ctx):
    # menu 1, time, label, repeat=3 (weekdays), sound/snooze/max defaults, confirm, exit
    ctx = make_ctx(["1", "07:30", "Gym", "3", "", "", "", "", "0"])
    out = run(ctx)
    (a,) = ctx.store.load_alarms()
    assert a.label == "Gym" and a.repeat == ["mon", "tue", "wed", "thu", "fri"]
    assert a.snooze_minutes == 5 and a.max_snoozes == 3 and a.sound == "default"
    assert "Alarm saved" in out and "Weekdays" in out


def test_add_once_defaults_to_next_occurrence(make_ctx):
    ctx = make_ctx(["1", "7:30 PM", "", "", "", "", "", "", "", "0"])
    # time, label(Enter), repeat(Enter=once), date(Enter), sound, snooze, max, confirm
    run(ctx)
    (a,) = ctx.store.load_alarms()
    assert a.label == "Alarm" and a.repeat == [] and str(a.time) == "19:30:00"
    assert a.date == ctx.clock.now().date()  # 19:30 is still ahead of 09:00


def test_invalid_time_reprompts_and_cancel_returns_to_menu(make_ctx):
    ctx = make_ctx(["1", "abc", "0"])  # '0' is not a valid time -> re-asks, then EOF cancels
    ctx.console.inputs += ["0"]
    run(ctx)
    assert "Invalid time" in ctx.console.text
    assert ctx.store.load_alarms() == []


def test_declining_save_discards(make_ctx):
    ctx = make_ctx(["1", "07:30", "", "2", "", "", "", "n", "0"])
    out = run(ctx)
    assert "Cancelled." in out and ctx.store.load_alarms() == []


def test_past_date_rejected(make_ctx):
    ctx = make_ctx(["1", "07:30", "", "1", "2020-01-01", "2030-01-01", "", "", "", "", "0"])
    out = run(ctx)
    assert "already in the past" in out
    assert str(ctx.store.load_alarms()[0].date) == "2030-01-01"


def seed(ctx, *specs, once=False):
    """Create alarms through the real menu flow (daily by default)."""
    for time_, label in specs:
        repeat = ["1", ""] if once else ["2"]  # once also asks for a date
        ctx.console.inputs += ["1", time_, label, *repeat, "", "", "", ""]
    ctx.console.inputs.append("0")
    run(ctx)


def test_list_delete_toggle_edit(make_ctx):
    ctx = make_ctx()
    seed(ctx, ("07:00", "First"), ("08:00", "Second"), ("22:00", "Third"))
    ctx.console.inputs += ["4", "2", "0"]  # list, show all, exit
    out = run(ctx)
    assert "First" in out and "Second" in out and "Third" in out

    # toggle alarm #1 (sorted by next trigger: 22:00 is today, 07:00/08:00 tomorrow)
    ctx.console.inputs += ["5", "1", "0"]
    run(ctx)
    states = {a.label: a.enabled for a in ctx.store.load_alarms()}
    assert states["Third"] is False and states["First"] is True

    # delete alarms 1 and 2 with confirmation
    ctx.console.inputs += ["3", "1,2", "y", "0"]
    run(ctx)
    assert len(ctx.store.load_alarms()) == 1

    # delete all, decline first
    ctx.console.inputs += ["3", "all", "n", "0"]
    run(ctx)
    assert len(ctx.store.load_alarms()) == 1


def test_edit_only_changes_label(make_ctx):
    ctx = make_ctx()
    seed(ctx, ("07:30", "Gym"), once=True)
    before = ctx.store.load_alarms()[0]
    # edit: pick alarm 1, field 2 (Label) -> "Run", then 7 (Save)
    ctx.console.inputs += ["2", "1", "2", "Run", "7", "0"]
    run(ctx)
    after = ctx.store.load_alarms()[0]
    assert after.label == "Run"
    assert (after.time, after.repeat, after.date, after.id) == (before.time, before.repeat, before.date, before.id)


def test_edit_time_reschedules_and_cancel_discards(make_ctx):
    ctx = make_ctx()
    seed(ctx, ("07:30", "Gym"), once=True)
    ctx.console.inputs += ["2", "1", "1", "23:15", "0", "0"]  # change time, then Cancel
    run(ctx)
    assert str(ctx.store.load_alarms()[0].time) == "07:30:00"
    ctx.console.inputs += ["2", "1", "1", "23:15", "7", "0"]
    run(ctx)
    a = ctx.store.load_alarms()[0]
    assert str(a.time) == "23:15:00" and a.date == ctx.clock.now().date()


def test_timer(make_ctx):
    ctx = make_ctx(["6", "10m", "Tea", "0"])
    run(ctx)
    (t,) = ctx.store.load_alarms()
    assert t.kind == "timer" and t.label == "Tea"
    due = ctx.clock.now() + timedelta(minutes=10)
    assert (t.date, str(t.time)) == (due.date(), due.strftime("%H:%M:%S"))


def test_next_history_settings_and_sound(make_ctx):
    ctx = make_ctx()
    seed(ctx, ("23:00", "Late"))
    ctx.console.inputs += ["8", "10", "11", "1", "10", "0", "11", "5", "0", "12", "10", "0"]
    out = run(ctx)
    assert "Next alarm:" in out and '"Late"' in out
    assert "No history yet." in out
    assert ctx.store.load_settings().snooze_minutes == 10
    assert ctx.store.load_settings().time_format == "12h"
    assert "backend: fake" in out
    assert ctx.player.calls == ["play:beep", "stop"]


def test_main_menu_invalid_choice_and_ctrl_c_exit(make_ctx):
    ctx = make_ctx(["99", "abc", "0"])
    out = run(ctx)
    assert "Enter a number between 0 and 12" in out
    ctx = make_ctx(["y"])  # EOF at the main prompt asks "Exit?"
    ctx.console.inputs = []
    assert run_menu(ctx) == 0  # EOF on both prompts exits cleanly


def test_empty_state_messages(make_ctx):
    ctx = make_ctx(["2", "3", "4", "5", "8", "0"])
    out = run(ctx)
    assert out.count("No alarms yet") == 4 and "No active alarms." in out
