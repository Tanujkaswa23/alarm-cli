"""Interactive prompt helpers.

Every helper re-asks on invalid input. Ctrl+C / end-of-input raises Cancelled.
A bracketed default is accepted with Enter.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date, time, timedelta
from pathlib import Path
from typing import TypeVar

from alarm_cli import parsing
from alarm_cli.errors import Cancelled, ValidationError

T = TypeVar("T")


def _read(console, prompt: str) -> str:
    try:
        return console.input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        console.print("")
        raise Cancelled from None


def ask(
    console,
    prompt: str,
    parse: Callable[[str], T],
    default: T | None = None,
    default_label: str | None = None,
) -> T:
    """Ask until `parse` accepts the answer. Enter returns `default` when given."""
    if default is not None or default_label is not None:
        shown = default_label if default_label is not None else str(default)
        suffix = f" [{shown}]"
    else:
        suffix = ""
    while True:
        raw = _read(console, f"{prompt}{suffix}: ")
        if raw == "":
            if default is not None:
                return default
            if default_label is not None:  # default is "none"
                return None  # type: ignore[return-value]
            console.print("A value is required.")
            continue
        try:
            return parse(raw)
        except ValidationError as exc:
            console.print(str(exc))


def ask_text(console, prompt: str, default: str | None = None, max_len: int = 60) -> str:
    def parse(raw: str) -> str:
        if len(raw) > max_len:
            raise ValidationError(f"Please use at most {max_len} characters.")
        return raw

    return ask(console, prompt, parse, default)


def ask_int(console, prompt: str, lo: int, hi: int, default: int | None = None) -> int:
    def parse(raw: str) -> int:
        try:
            value = int(raw)
        except ValueError:
            raise ValidationError("Please enter a whole number.") from None
        if not lo <= value <= hi:
            raise ValidationError(f"Enter a number between {lo} and {hi}.")
        return value

    return ask(console, prompt, parse, default)


def ask_yes_no(console, prompt: str, default: bool = False) -> bool:
    def parse(raw: str) -> bool:
        r = raw.lower()
        if r in ("y", "yes"):
            return True
        if r in ("n", "no"):
            return False
        raise ValidationError("Please answer y or n.")

    hint = "Y/n" if default else "y/N"
    return ask(console, prompt, parse, default, default_label=hint)


def ask_choice(
    console,
    options: list[str],
    title: str | None = None,
    default: int | None = 1,
    back_label: str = "Back",
) -> int:
    """Show a numbered list and return the 0-based index. `0` cancels."""
    if title:
        console.print(title)
    for i, opt in enumerate(options, 1):
        console.print(f" {i}. {opt}")
    console.print(f" 0. {back_label}")

    def parse(raw: str) -> int:
        try:
            n = int(raw)
        except ValueError:
            raise ValidationError("Please enter a number from the list.") from None
        if n == 0:
            raise Cancelled
        if not 1 <= n <= len(options):
            raise ValidationError(f"Choose a number between 0 and {len(options)}.")
        return n - 1

    result = ask(console, "Choose", parse, None if default is None else default - 1,
                 default_label=None if default is None else str(default))
    return result


def ask_selection(console, prompt: str, count: int, multi: bool = True) -> list[int]:
    """Pick alarms by list number: `2`, `1,3` or `all` (returns 0-based indexes)."""

    def parse(raw: str) -> list[int]:
        r = raw.lower()
        if r == "0":
            raise Cancelled
        if not multi and ("," in r or r == "all"):
            raise ValidationError("Enter a single alarm number.")
        if r == "all":
            return list(range(count))
        picked: list[int] = []
        for tok in r.replace(" ", "").split(","):
            if not tok.isdigit() or not 1 <= int(tok) <= count:
                raise ValidationError(f"Enter numbers between 1 and {count}, e.g. 2 or 1,3 or all.")
            if int(tok) - 1 not in picked:
                picked.append(int(tok) - 1)
        return picked

    return ask(console, prompt, parse)


def ask_time(console, prompt: str, default: time | None = None, fmt: str = "24h") -> time:
    label = parsing.format_time(default, fmt) if default else None
    return ask(console, prompt, parsing.parse_time, default, label)


def ask_duration(console, prompt: str) -> timedelta:
    return ask(console, prompt, parsing.parse_duration)


def ask_optional_date(
    console,
    prompt: str,
    default: date | None,
    validate: Callable[[date], None] | None = None,
    none_label: str = "next occurrence",
) -> date | None:
    def parse(raw: str) -> date:
        d = parsing.parse_date(raw)
        if validate:
            validate(d)
        return d

    label = default.isoformat() if default else none_label
    return ask(console, prompt, parse, default, label)


def ask_days(console, prompt: str = "Days (e.g. mon,wed,fri)") -> list[str]:
    return ask(console, prompt, parsing.parse_days)


def ask_wav_path(console, prompt: str = "Path to .wav file") -> str:
    def parse(raw: str) -> str:
        path = Path(raw.strip('"')).expanduser()
        if not path.is_file():
            raise ValidationError("File not found.")
        if path.suffix.lower() != ".wav":
            raise ValidationError("Only .wav files are supported.")
        return str(path.resolve())

    return ask(console, prompt, parse)
