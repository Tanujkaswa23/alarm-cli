# alarm-cli

A menu-driven alarm clock for the terminal. No GUI, no web UI, no database, and no
third-party runtime dependencies: you pick actions by number, answer a few prompts, and
alarms are kept in plain JSON files.

```
===================== CLI ALARM CLOCK ======================
 Now: Wed 28 Oct 2026  09:14:05     Active alarms: 2
 Next: "Gym" at Thu 29 Oct 07:30 (in 22h 16m)
 (Alarms only ring while Ring mode is running - option 7)
------------------------------------------------------------
  1. Add alarm
  2. Edit alarm
  3. Delete alarm
  4. List alarms
  5. Enable / disable alarm
  6. Set timer
  7. Start ring mode  (watch & ring alarms)
  8. Show next alarm
  9. Live clock
 10. History
 11. Settings
 12. Test sound
  0. Exit
------------------------------------------------------------
Choose an option [0-12]:
```

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Using the menu](#using-the-menu)
- [Ring mode](#ring-mode)
- [Input formats](#input-formats)
- [Settings](#settings)
- [Sound](#sound)
- [Where data is stored](#where-data-is-stored)
- [How it works](#how-it-works)
- [Project layout](#project-layout)
- [Development and tests](#development-and-tests)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)

## Features

- One-time alarms, daily, weekdays, weekends, or custom days (`mon,wed,fri`).
- Optional label, explicit date, per-alarm sound, snooze length and snooze limit.
- Countdown timers (`90s`, `10m`, `1h30m`, `00:05:00`).
- Ring mode with a live countdown to the next alarm, snooze and dismiss from the keyboard.
- Late-start handling: alarms that came due just before you started ring mode still ring;
  older ones are recorded as missed instead of being replayed.
- Alarms added or changed in another terminal are picked up by a running ring mode.
- History of fired, snoozed, dismissed and missed events (last 100).
- Settings for default snooze, auto-stop, grace window, default sound and 12h/24h display.
- Safe storage: atomic writes, and a corrupt file is backed up as `.bak` instead of crashing.
- Works on Windows, macOS and Linux (Windows is the primary development platform).

## Requirements

- Python 3.10 or newer.
- Nothing else at runtime (standard library only). `pytest` is needed only to run the tests.

## Installation

```bash
git clone https://github.com/Tanujkaswa23/alarm_clock.git
cd alarm_clock

python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

pip install -e .          # add ".[dev]" to also install pytest
```

This installs an `alarm` command. You can also run it without installing:

```bash
python -m alarm_cli       # from the repo root, with PYTHONPATH=src if not installed
```

## Quick start

1. Run `alarm`.
2. Type `1` and Enter (Add alarm), then answer the prompts. Press Enter to accept the
   value in brackets:

   ```
   Time (HH:MM or h:MM AM/PM): 07:30
   Label [Alarm]: Gym
   Repeat:
    1. Once
    2. Every day
    3. Weekdays (Mon-Fri)
    4. Weekends
    5. Custom days
    0. Back
   Choose [1]: 3
   Sound: ...                       -> Enter for the default
   Snooze minutes [5]:              -> Enter
   Max snoozes (0 = unlimited) [3]: -> Enter
   Save this alarm? [Y/n]:          -> Enter
   Alarm saved: 07:30 "Gym" (Weekdays) - next in 22h 16m (Thu 29 Oct 07:30)
   ```
3. Type `7` to start **ring mode** and leave the terminal open. Alarms only ring while
   ring mode is running.

## Using the menu

Everything is chosen by number. These rules apply to every prompt:

| Rule | Behaviour |
|------|-----------|
| Default in `[brackets]` | Press Enter to accept it |
| Invalid input | A one-line message, then the same question again |
| `0` in a numbered list | Go back / cancel |
| Ctrl+C at any prompt | Cancel the current action and return to the main menu |
| Ctrl+C at the main menu | Asks `Exit? [y/N]` |

### 1. Add alarm
Prompts for time, label, repeat, date (only for "Once"), sound, snooze minutes and max
snoozes, then shows a summary and asks to save. A one-time alarm without a date fires at the
next occurrence of that time (today if still ahead, otherwise tomorrow). Dates in the past
are rejected.

### 2. Edit alarm
Pick an alarm by its number in the list, then use the field menu to change only what you
need (time, label, repeat/date, sound, snooze minutes, max snoozes). Choose **Save & finish**
to apply or **Cancel** to discard. Changing the time or repeat restarts the schedule, and a
finished or missed one-time alarm becomes active again.

### 3. Delete alarm
Choose by number: `2`, several with `1,3`, or `all`. A `y/N` confirmation follows.

### 4. List alarms
Shows active alarms, or all (including disabled / done / missed). Columns: number, ID, time,
label, repeat, state and next trigger with time remaining.

```
 No.  ID      Time      Label        Repeat    State    Next
 ---  ------  --------  -----------  --------  -------  -------------------------------
 1    5d7afc  03:56:23  [timer] Tea  Once      Enabled  Wed 28 Oct 03:56:23 (in 9m 59s)
 2    caa5bc  07:30     Gym          Weekdays  Enabled  Thu 29 Oct 07:30 (in 22h 16m)
```

Numbers are positions in the list you are looking at (sorted by next trigger); they are not
stored. The ID is a short internal identifier shown for reference.

### 5. Enable / disable alarm
Flips the state of the chosen alarm(s). Re-enabling an alarm restarts its schedule from now,
so it never replays occurrences it missed while disabled.

### 6. Set timer
Enter a duration and an optional label. A timer is stored as a one-time alarm at an absolute
time, so it survives restarting the app. It only rings while ring mode is running.

### 7. Start ring mode
See [Ring mode](#ring-mode).

### 8. Show next alarm
Prints the next alarm and the time remaining.

### 9. Live clock
A live-updating clock. Press any key to return.

### 10. History
The 20 most recent events (newest first), with options to show all 100 or clear them.
Events: `fired`, `snoozed`, `dismissed`, `missed`.

### 11. Settings
See [Settings](#settings).

### 12. Test sound
Plays the default sound for about three seconds and reports which audio backend was used.

## Ring mode

Ring mode is a foreground loop that watches the clock. A terminal program cannot ring while
it is waiting at a menu prompt, so alarms ring **only while ring mode is running**.

While idle:

```
 Next: Gym at 07:30 (in 02:14:09)   [m] menu
```

| Key | Action |
|-----|--------|
| `m` | Return to the main menu |
| Ctrl+C | Leave ring mode (back to the menu) |

When an alarm is due, the sound repeats and this is shown:

```
 *** ALARM 07:30 - Gym ***
 [s] snooze 5m (3 left)   [d] dismiss
```

| Key | Action |
|-----|--------|
| `s` | Snooze for the alarm's snooze length (ring again afterwards) |
| `d` or Enter | Dismiss |

- **Snooze limit:** after the alarm's max snoozes are used, `s` reports "No snoozes left".
  `0` means unlimited. During a snooze you can still press `d` to dismiss.
- **Auto-stop:** if you do nothing for the auto-stop time (default 60 s) the sound stops and
  the alarm is recorded as **missed**.
- **After ringing:** one-time alarms and timers are finished (state `done`, or `missed`).
  Recurring alarms stay active and move on to their next occurrence.
- **Several alarms at the same moment** ring together as one prompt.
- **Late start:** when ring mode starts, an alarm that came due within the grace window
  (default 5 minutes) rings immediately. Older ones are recorded as missed, once, with no
  burst of replays, and recurring ones continue from their next occurrence.
- **Live reload:** ring mode re-reads the alarm file when it changes, so you can add or edit
  alarms from a second terminal without restarting it.

## Input formats

| Field | Accepted values | Examples |
|-------|-----------------|----------|
| Time | 24h `HH:MM` or `HH:MM:SS`; 12h `h:MM AM/PM` | `07:30`, `23:59:59`, `7:30 PM`, `7pm` |
| Date | `YYYY-MM-DD` (must be in the future) | `2026-12-25` |
| Custom days | Comma or space separated; short or full names | `mon,wed,fri`, `Saturday sunday` |
| Duration | `h`/`m`/`s` parts, `HH:MM:SS`, or a bare number (minutes); max 24 h | `90s`, `10m`, `1h30m`, `00:05:00`, `45` |
| Label | Up to 60 characters | `Call mom` |
| Snooze minutes | 1-60 | `5` |
| Max snoozes | 0-20 (0 = unlimited) | `3` |
| Sound file | Path to an existing `.wav` file | `C:\sounds\wake.wav` |

## Settings

Menu option 11. Values are saved immediately.

| Setting | Default | Range | Meaning |
|---------|---------|-------|---------|
| Default snooze minutes | 5 | 1-60 | Pre-filled when adding an alarm |
| Auto-stop ringing after | 60 s | 10-3600 | Unattended alarms stop and are marked missed |
| Late-start grace | 5 min | 0-120 | How late an alarm may still ring when ring mode starts |
| Default sound | built-in beep | beep or `.wav` | Used by alarms set to "Default sound" |
| Time display | 24h | 24h / 12h | How times are shown (input accepts both) |

## Sound

Each alarm can use the default sound, a custom `.wav` file, or be silent (visual only).
The player degrades gracefully:

| Platform | Beep | `.wav` file |
|----------|------|-------------|
| Windows | `winsound.Beep` | `winsound.PlaySound` |
| macOS | terminal bell | `afplay` |
| Linux | terminal bell | `paplay` or `aplay` |
| No audio available | terminal bell (`\a`) | falls back to beep |

Use menu option 12 to check what you will hear.

## Where data is stored

Three plain files in one folder:

| Platform | Default folder |
|----------|----------------|
| Windows | `%APPDATA%\alarm-cli` |
| macOS | `~/Library/Application Support/alarm-cli` |
| Linux | `$XDG_CONFIG_HOME/alarm-cli` or `~/.config/alarm-cli` |

Set the `ALARM_CLI_HOME` environment variable to use a different folder.

| File | Content |
|------|---------|
| `alarms.json` | All alarms and timers |
| `settings.json` | Settings |
| `history.jsonl` | Last 100 events, one JSON object per line |

Files are written atomically (temp file, then replace). If a file cannot be parsed it is
renamed to `<name>.bak`, a warning is printed, and the app starts with defaults.

Set `ALARM_CLI_DEBUG=1` to see full tracebacks instead of a one-line error.

## How it works

- **Scheduling** (`scheduler.py`) is pure and uses timezone-aware local datetimes. An alarm
  remembers when it was created and when it last fired; the next occurrence is the first one
  strictly after that moment, so each occurrence fires exactly once.
- **Ring engine** (`engine.py`) ticks about twice a second, finds due alarms, and runs a small
  state machine: ringing, snoozed, then dismissed or missed.
- **Snoozes** are held in memory only; if you quit ring mode during a snooze, that alarm is
  not re-rung.
- **Testability:** the clock, console, keyboard and sound player are injected, so the tests
  drive the whole app with a fake clock and scripted keys, with no real waiting or audio.

## Project layout

```
src/alarm_cli/
  app.py          main menu loop and entry point
  prompts.py      input helpers: defaults, re-ask on invalid input, cancel
  actions/        menu items (alarms, timer, watch, settings, shared field prompts)
  engine.py       ring mode: detection, ringing, snooze, dismiss, auto-stop
  scheduler.py    next-occurrence logic (pure)
  parsing.py      time / duration / date / day parsing and formatting (pure)
  models.py       Alarm, Settings, HistoryEvent
  storage.py      JSON persistence
  ringer.py       sound playback backends
  keys.py         non-blocking key reader (msvcrt / termios)
  render.py       header and alarm table
  console.py      stdin/stdout wrapper, in-place status line
  clock.py        system clock and fake clock for tests
tests/            pytest suite
docs/SPEC.md      requirements, design and implementation plan
```

## Development and tests

```bash
pip install -e ".[dev]"
python -m pytest
```

The suite covers parsing, scheduling (weekday skipping, month/year rollover, stale
occurrences), storage (atomic writes, corrupt files, history trimming), prompts, scripted
menu sessions, and the ring engine (ring, snooze, max snoozes, auto-stop, late start,
simultaneous alarms, live reload).

Requirements and design notes are in [docs/SPEC.md](docs/SPEC.md).
