"""Menu items 10-11: history and settings."""
from __future__ import annotations

from datetime import datetime

from alarm_cli import prompts
from alarm_cli.context import Context
from alarm_cli.errors import Cancelled


def show_history(ctx: Context) -> None:
    c = ctx.console
    events = list(reversed(ctx.store.load_history()))
    if not events:
        c.print("No history yet.")
        return

    def show(items) -> None:
        for e in items:
            stamp = datetime.fromisoformat(e.ts).strftime("%Y-%m-%d %H:%M:%S")
            c.print(f" {stamp}  {e.event:<10} {e.label}")

    show(events[:20])
    choice = prompts.ask_choice(c, ["Show all (up to 100)", "Clear history"], default=None)
    if choice == 0:
        show(events)
    elif prompts.ask_yes_no(c, "Clear all history?", False):
        ctx.store.clear_history()
        c.print("History cleared.")


def edit_settings(ctx: Context) -> None:
    c = ctx.console
    while True:
        s = ctx.store.load_settings()
        options = [
            f"Default snooze minutes [{s.snooze_minutes}]",
            f"Auto-stop ringing after (seconds) [{s.auto_stop_seconds}]",
            f"Late-start grace (minutes) [{s.grace_minutes}]",
            f"Default sound [{s.default_sound}]",
            f"Time display [{s.time_format}] (toggle 24h / 12h)",
        ]
        try:
            choice = prompts.ask_choice(c, options, "Settings:", default=None)
        except Cancelled:
            return
        if choice == 0:
            s.snooze_minutes = prompts.ask_int(c, "Default snooze minutes", 1, 60, s.snooze_minutes)
        elif choice == 1:
            s.auto_stop_seconds = prompts.ask_int(c, "Auto-stop after seconds", 10, 3600, s.auto_stop_seconds)
        elif choice == 2:
            s.grace_minutes = prompts.ask_int(c, "Grace minutes", 0, 120, s.grace_minutes)
        elif choice == 3:
            kind = prompts.ask_choice(c, ["Built-in beep", "Custom .wav file"], "Sound:", default=1)
            s.default_sound = "beep" if kind == 0 else prompts.ask_wav_path(c)
        else:
            s.time_format = "12h" if s.time_format == "24h" else "24h"
        ctx.store.save_settings(s)
        c.print("Setting saved.")
