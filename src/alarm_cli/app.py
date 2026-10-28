"""Entry point: numbered main menu loop."""
from __future__ import annotations

import os
import sys

from alarm_cli import prompts
from alarm_cli.actions import alarms, settings, timer, watch
from alarm_cli.clock import SystemClock
from alarm_cli.console import Console
from alarm_cli.context import Context
from alarm_cli.errors import AlarmError, Cancelled
from alarm_cli.keys import KeyReader
from alarm_cli.render import WIDTH, header
from alarm_cli.ringer import SoundPlayer
from alarm_cli.storage import JsonStore

MENU = [
    ("Add alarm", alarms.add_alarm),
    ("Edit alarm", alarms.edit_alarm),
    ("Delete alarm", alarms.delete_alarm),
    ("List alarms", alarms.list_alarms),
    ("Enable / disable alarm", alarms.toggle_alarm),
    ("Set timer", timer.set_timer),
    ("Start ring mode  (watch & ring alarms)", watch.ring_mode),
    ("Show next alarm", watch.show_next),
    ("Live clock", watch.live_clock),
    ("History", settings.show_history),
    ("Settings", settings.edit_settings),
    ("Test sound", watch.test_sound),
]


def _show_menu(ctx: Context) -> None:
    c = ctx.console
    c.print("")
    for line in header(ctx.store.load_alarms(), ctx.clock.now(), ctx.store.load_settings()):
        c.print(line)
    for i, (title, _) in enumerate(MENU, 1):
        c.print(f" {i:>2}. {title}")
    c.print("  0. Exit")
    c.print("-" * WIDTH)


def run_menu(ctx: Context) -> int:
    c = ctx.console
    while True:
        _show_menu(ctx)
        try:
            choice = prompts.ask_int(c, f"Choose an option [0-{len(MENU)}]", 0, len(MENU))
        except Cancelled:  # Ctrl+C / end of input at the main prompt
            try:
                if prompts.ask_yes_no(c, "Exit?", False):
                    return 0
            except Cancelled:
                return 0
            continue
        if choice == 0:
            c.print("Goodbye.")
            return 0
        _, handler = MENU[choice - 1]
        try:
            handler(ctx)
        except Cancelled:
            c.print("Cancelled.")
        except KeyboardInterrupt:
            c.print("Back to menu.")
        except (AlarmError, OSError) as exc:
            c.print(f"Error: {exc}")


def main(argv: list[str] | None = None) -> int:
    ctx = Context(Console(), JsonStore(), SystemClock(), SoundPlayer(), KeyReader())
    try:
        return run_menu(ctx)
    except Exception as exc:  # noqa: BLE001 - last-resort one-line error
        if os.environ.get("ALARM_CLI_DEBUG") == "1":
            raise
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
    finally:
        ctx.player.stop()


if __name__ == "__main__":
    raise SystemExit(main())
