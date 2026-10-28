from __future__ import annotations

from alarm_cli import prompts
from alarm_cli.context import Context
from alarm_cli.models import Alarm
from alarm_cli.render import alarm_table, sorted_alarms


def pick_alarms(ctx: Context, prompt: str, multi: bool = True) -> list[Alarm] | None:
    """Show all alarms numbered and let the user choose; None when there are none."""
    c = ctx.console
    alarms = sorted_alarms(ctx.store.load_alarms(), ctx.clock.now())
    if not alarms:
        c.print("No alarms yet. Use option 1 to add one.")
        return None
    settings = ctx.store.load_settings()
    for line in alarm_table(alarms, ctx.clock.now(), settings):
        c.print(" " + line)
    hint = " (e.g. 2 or 1,3 or all, 0 = back)" if multi else " (0 = back)"
    chosen = prompts.ask_selection(c, prompt + hint, len(alarms), multi)
    return [alarms[i] for i in chosen]
