"""Menu items 7-9 and 12: ring mode, next alarm, live clock, test sound."""
from __future__ import annotations

from alarm_cli.context import Context
from alarm_cli.engine import Engine
from alarm_cli.render import describe_next, next_alarm


def ring_mode(ctx: Context) -> None:
    try:
        Engine(ctx).run()
    except KeyboardInterrupt:
        ctx.player.stop()
        ctx.console.clear_status()
        ctx.console.print("Left ring mode.")


def show_next(ctx: Context) -> None:
    now = ctx.clock.now()
    nxt = next_alarm(ctx.store.load_alarms(), now)
    if not nxt:
        ctx.console.print("No active alarms.")
        return
    ctx.console.print("Next alarm: " + describe_next(*nxt, now, ctx.store.load_settings()))


def live_clock(ctx: Context) -> None:
    c = ctx.console
    fmt = "%H:%M:%S" if ctx.store.load_settings().time_format == "24h" else "%I:%M:%S %p"
    c.print(" Live clock - press any key to return.")
    try:
        with ctx.keys:
            while ctx.keys.poll() is None:
                c.status("  " + ctx.clock.now().strftime("%a %d %b %Y   " + fmt))
                ctx.clock.sleep(0.2)
    finally:
        c.clear_status()


def test_sound(ctx: Context) -> None:
    c = ctx.console
    settings = ctx.store.load_settings()
    sound = settings.default_sound
    c.print("Playing sound for 3 seconds...")
    ctx.player.play(sound)
    try:
        ctx.clock.sleep(3)
    finally:
        ctx.player.stop()
    c.print(f"Done (backend: {ctx.player.backend}). If you heard nothing, check volume or choose a .wav in Settings.")
