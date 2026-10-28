"""Menu items 1-5: add, edit, delete, list, enable/disable."""
from __future__ import annotations

import dataclasses

from alarm_cli import prompts
from alarm_cli.actions import fields
from alarm_cli.actions.common import pick_alarms
from alarm_cli.context import Context
from alarm_cli.errors import Cancelled
from alarm_cli.models import Alarm
from alarm_cli.parsing import describe_repeat, format_remaining, format_time
from alarm_cli.render import alarm_table, sorted_alarms
from alarm_cli.scheduler import next_trigger, reschedule, revive


def _summary(a: Alarm, fmt: str) -> str:
    when = describe_repeat(a.repeat) if a.repeat else (a.date.isoformat() if a.date else "next occurrence")
    return (
        f'{format_time(a.time, fmt)} "{a.label}" repeat: {when}, sound: {fields.sound_label(a.sound)}, '
        f"snooze: {a.snooze_minutes}m x{a.max_snoozes or 'unlimited'}"
    )


def _saved_message(ctx: Context, a: Alarm, verb: str) -> str:
    now = ctx.clock.now()
    nxt = next_trigger(a, now)
    tail = f" - next in {format_remaining(nxt - now)} ({nxt.strftime('%a %d %b %H:%M')})" if nxt else ""
    return f"{verb}: {format_time(a.time, ctx.store.load_settings().time_format)} \"{a.label}\" ({describe_repeat(a.repeat)}){tail}"


def add_alarm(ctx: Context) -> None:
    c = ctx.console
    settings = ctx.store.load_settings()
    now = ctx.clock.now()
    at = fields.ask_alarm_time(ctx)
    label = fields.ask_label(ctx)
    repeat, date = fields.ask_repeat(ctx, at, now)
    sound = fields.ask_sound(ctx)
    snooze = fields.ask_snooze(ctx, settings.snooze_minutes)
    max_snoozes = fields.ask_max_snoozes(ctx, 3)

    alarms = ctx.store.load_alarms()
    alarm = Alarm(
        id=ctx.store.new_id(alarms), time=at, label=label, repeat=repeat, date=date,
        sound=sound, snooze_minutes=snooze, max_snoozes=max_snoozes,
    )
    reschedule(alarm, now)
    c.print("Summary: " + _summary(alarm, settings.time_format))
    if not prompts.ask_yes_no(c, "Save this alarm?", True):
        raise Cancelled
    alarms.append(alarm)
    ctx.store.save_alarms(alarms)
    c.print(_saved_message(ctx, alarm, "Alarm saved"))


def edit_alarm(ctx: Context) -> None:
    c = ctx.console
    picked = pick_alarms(ctx, "Edit which alarm", multi=False)
    if not picked:
        return
    original = picked[0]
    alarm = dataclasses.replace(original, repeat=list(original.repeat))
    now = ctx.clock.now()
    fmt = ctx.store.load_settings().time_format
    schedule_changed = False

    while True:
        options = [
            f"Time [{format_time(alarm.time, fmt)}]",
            f"Label [{alarm.label}]",
            f"Repeat / date [{describe_repeat(alarm.repeat)}{' ' + alarm.date.isoformat() if alarm.date and not alarm.repeat else ''}]",
            f"Sound [{fields.sound_label(alarm.sound)}]",
            f"Snooze minutes [{alarm.snooze_minutes}]",
            f"Max snoozes [{alarm.max_snoozes}]",
            "Save & finish",
        ]
        choice = prompts.ask_choice(
            c, options, f'Editing "{alarm.label}":', default=None, back_label="Cancel (discard changes)"
        )
        if choice == 0:
            alarm.time = fields.ask_alarm_time(ctx, alarm.time)
            if not alarm.repeat:
                alarm.date = None  # re-resolve to the next occurrence of the new time
            schedule_changed = True
        elif choice == 1:
            alarm.label = fields.ask_label(ctx, alarm.label)
        elif choice == 2:
            alarm.repeat, alarm.date = fields.ask_repeat(ctx, alarm.time, now, alarm.repeat, alarm.date)
            schedule_changed = True
        elif choice == 3:
            alarm.sound = fields.ask_sound(ctx, alarm.sound)
        elif choice == 4:
            alarm.snooze_minutes = fields.ask_snooze(ctx, alarm.snooze_minutes)
        elif choice == 5:
            alarm.max_snoozes = fields.ask_max_snoozes(ctx, alarm.max_snoozes)
        else:
            break

    if schedule_changed:
        if alarm.state != "active":
            alarm.enabled = True
        reschedule(alarm, now)
    alarms = ctx.store.load_alarms()
    ctx.store.save_alarms([alarm if a.id == alarm.id else a for a in alarms])
    c.print(_saved_message(ctx, alarm, "Alarm updated"))


def delete_alarm(ctx: Context) -> None:
    c = ctx.console
    picked = pick_alarms(ctx, "Delete which")
    if not picked:
        return
    if not prompts.ask_yes_no(c, f"Delete {len(picked)} alarm(s)?", False):
        raise Cancelled
    ids = {a.id for a in picked}
    ctx.store.save_alarms([a for a in ctx.store.load_alarms() if a.id not in ids])
    c.print(f"Deleted {len(ids)} alarm(s).")


def list_alarms(ctx: Context) -> None:
    c = ctx.console
    alarms = ctx.store.load_alarms()
    if not alarms:
        c.print("No alarms yet. Use option 1 to add one.")
        return
    show = prompts.ask_choice(c, ["Active only", "All (including disabled / done)"], "Show:", default=1)
    now = ctx.clock.now()
    if show == 0:
        alarms = [a for a in alarms if a.enabled and a.state == "active"]
    alarms = sorted_alarms(alarms, now)
    if not alarms:
        c.print("No active alarms.")
        return
    for line in alarm_table(alarms, now, ctx.store.load_settings()):
        c.print(" " + line)


def toggle_alarm(ctx: Context) -> None:
    c = ctx.console
    picked = pick_alarms(ctx, "Toggle which")
    if not picked:
        return
    now = ctx.clock.now()
    ids = {a.id for a in picked}
    alarms = ctx.store.load_alarms()
    for a in alarms:
        if a.id not in ids:
            continue
        if a.enabled and a.state == "active":
            a.enabled = False
        else:
            revive(a, now)  # also revives done / missed one-time alarms
        c.print(f'"{a.label}" is now {"enabled" if a.enabled else "disabled"}.')
    ctx.store.save_alarms(alarms)
