# CLI Alarm Clock — Requirements, Design & Implementation Plan

Scope: terminal-only alarm clock in Python. No web UI, no GUI, no database.
Interaction model: **numbered interactive menu** (no command-line flags to memorise).
Target: Python 3.10+, Windows / macOS / Linux (Windows is the primary dev platform).

---

# Part 1 — Requirements

## 1.1 Overview

The user starts the app with `alarm` (or `python -m alarm_cli`) and gets a numbered
main menu. They type a number to pick an action (add, edit, delete, list, ...) and
are then walked through guided prompts with sensible defaults. A "ring mode" watches
the clock, rings when an alarm is due, and lets the user snooze or dismiss from the
keyboard. Alarm definitions persist in a single JSON file between sessions.

## 1.2 Key architectural constraint

A terminal program can only ring while it is running and not blocked on a prompt.
Decision: **menu mode** is for managing alarms; **ring mode** (menu option 7) is a
foreground loop that watches the clock and rings. Pressing `m` in ring mode returns
to the menu. The main menu header always shows whether any alarm is armed and the
next trigger time, with a reminder that alarms only ring in ring mode. No OS service
or background daemon in v1.

## 1.3 Functional requirements

### Menu & interaction
| ID | Requirement |
|----|-------------|
| FR-1 | Running `alarm` with no arguments shows the main menu and loops until the user chooses `0` (Exit). |
| FR-2 | Every action is selected by number; every sub-prompt that offers choices is numbered too (e.g. repeat options, sound options, which alarm to edit). |
| FR-3 | Every field prompt shows a default in brackets; pressing Enter accepts it. |
| FR-4 | Invalid input shows a one-line message and re-asks the same question (never crashes or exits). |
| FR-5 | Ctrl+C at any prompt cancels the current action and returns to the main menu; entering `0` at a selection list also goes back. |
| FR-6 | Destructive actions (delete) require a `y/N` confirmation. |
| FR-7 | Header on the main menu shows current time, count of active alarms, and next alarm with time remaining. |

### Alarm management
| ID | Requirement |
|----|-------------|
| FR-8 | Add an alarm with a time of day (24h `HH:MM`, optional seconds, or 12h `h:MM AM/PM`). |
| FR-9 | Optional label/message (default: "Alarm"). |
| FR-10 | Repeat chosen from a numbered list: once, daily, weekdays, weekends, or custom days (`mon,wed,fri`). |
| FR-11 | A one-time alarm fires at the next occurrence of that time (today if still in future, else tomorrow). Optional explicit date (`YYYY-MM-DD`). |
| FR-12 | Alarms are identified by their list number in all prompts; an internal short unique ID (e.g. `a1b2c3`) is stored and shown in the list for reference. |
| FR-13 | List alarms: no., time, label, repeat, state, next trigger and time remaining. |
| FR-14 | Delete one, several (`1,3`) or all alarms. |
| FR-15 | Enable / disable an alarm without deleting it. |
| FR-16 | Edit an existing alarm: pick it from the list, then each field is offered with its current value as the default (Enter keeps it). |
| FR-17 | Per-alarm options: sound choice, snooze duration, max snoozes. |

### Timers
| ID | Requirement |
|----|-------------|
| FR-18 | Start a countdown timer from a duration (`90s`, `10m`, `1h30m`, `00:05:00`; bare number = minutes). Stored as a one-time alarm with an absolute trigger time. |
| FR-19 | Ring mode shows a live countdown to the next alarm/timer. |

### Ringing
| ID | Requirement |
|----|-------------|
| FR-20 | When an alarm is due in ring mode: sound plays repeatedly and a prominent message shows label and time. |
| FR-21 | While ringing, keys: `s` snooze, `d`/Enter dismiss. While idle in ring mode: `m` back to menu. |
| FR-22 | Snooze re-rings after the alarm's snooze duration (default 5 min). Snoozing does not change the stored schedule. |
| FR-23 | If not acknowledged within an auto-stop period (default 60 s), ringing stops and the alarm is marked "missed" and logged. |
| FR-24 | After a one-time alarm is dismissed it is auto-disabled (state `done`); recurring alarms compute the next occurrence. |
| FR-25 | On entering ring mode, alarms that came due within a grace window (default 5 min) ring immediately; older ones are marked missed. |
| FR-26 | Multiple alarms due at the same time ring together as one prompt. |
| FR-27 | Sound: built-in beep pattern by default; optional `.wav` path; fallback to terminal bell (`\a`). "Silent" option = visual only. |
| FR-28 | Menu action "Test sound" plays the current sound for a few seconds. |

### Info & utility
| ID | Requirement |
|----|-------------|
| FR-29 | "Next alarm" action prints the next alarm and time remaining. |
| FR-30 | "Live clock" action shows a live-updating current time (Ctrl+C returns to menu). |
| FR-31 | "History" action shows the last events (fired / snoozed / dismissed / missed). |
| FR-32 | "Settings" action: default snooze, default sound, auto-stop seconds, grace window, 12h/24h display. |

### Persistence
| ID | Requirement |
|----|-------------|
| FR-33 | Alarms, settings and history are plain JSON files in the per-user data dir (`%APPDATA%\alarm-cli` on Windows, `~/.config/alarm-cli` or `~/Library/Application Support/alarm-cli` elsewhere). Override with env var `ALARM_CLI_HOME`. |
| FR-34 | Writes are atomic (temp file then replace) so a crash never corrupts data. |
| FR-35 | Ring mode re-reads the alarm file when its mtime changes, so alarms added from a second terminal take effect. |
| FR-36 | History keeps the last 100 events. |

## 1.4 Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Standard library only for core (`json`, `datetime`, `zoneinfo`, `msvcrt`/`termios`, `winsound`). Optional extra: `rich` for tables/colour, with plain-text fallback. |
| NFR-2 | Clear errors: one-line messages, tracebacks only if env `ALARM_CLI_DEBUG=1`. |
| NFR-3 | Exit code `0` on normal exit, `1` on unexpected fatal error. |
| NFR-4 | Ring timing accurate to within 1 s; loop sleeps ≤ 0.5 s per tick, idle CPU < 1%. |
| NFR-5 | Uses system local timezone; handles DST via timezone-aware datetimes. |
| NFR-6 | Testable: clock, sound, key input and prompt I/O are injectable; scheduling logic has no I/O. ≥ 85% coverage on scheduler/engine. |
| NFR-7 | Cross-platform keyboard input and sound with graceful degradation. |
| NFR-8 | Installable as a package exposing an `alarm` console script. |
| NFR-9 | Menu screens fit in an 80×24 terminal. |

## 1.5 Out of scope (v1)

Web/GUI, database, OS-level background service, cloud sync, email/SMS/desktop
notifications, multiple timezones per alarm, natural-language input, command-line
flags/sub-commands (menu only).

## 1.6 Acceptance examples

1. Run `alarm`, choose `1`, answer the prompts → alarm appears under `4` (List) with its next trigger.
2. Choose `6` (Timer), enter `10m`, choose `7` (Ring mode) → rings after 10 minutes; `s` re-rings after the snooze time.
3. Choose `2` (Edit), pick alarm `1`, press Enter on every field except Label → only the label changes.
4. Type `abc` at a time prompt → message "Invalid time" and the prompt repeats.
5. Corrupt/empty JSON file → friendly warning, file backed up as `alarms.json.bak`, app starts with no alarms.

---

# Part 2 — Design

## 2.1 Main menu

```
==================== CLI ALARM CLOCK ====================
 Now: Tue 28 Oct 2026 09:14:05     Active alarms: 2
 Next: "Gym" at Wed 07:30 (in 22h 16m)
 (Alarms only ring while Ring mode is running - option 7)
---------------------------------------------------------
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
---------------------------------------------------------
Choose an option [0-12]:
```

General prompt conventions (apply everywhere):
- `Label [Alarm]:` — text in brackets is the default; Enter accepts it.
- Numbered choice lists accept a number; `0` = back/cancel.
- Ctrl+C = cancel the current action, return to main menu.
- Invalid input → red/plain message + same prompt again.

### 1. Add alarm
Guided prompts, in order:

| # | Prompt | Accepts | Default |
|---|--------|---------|---------|
| 1 | `Time (HH:MM or h:MM AM/PM):` | `07:30`, `07:30:15`, `7:30 PM` | required |
| 2 | `Label [Alarm]:` | any text (≤ 60 chars), e.g. `Call mom` | `Alarm` |
| 3 | `Repeat:` numbered list below | 1–5 | `1` |
| 4 | `Date (YYYY-MM-DD) [next occurrence]:` — asked only if Repeat = once | date or Enter | next occurrence |
| 5 | `Sound:` numbered list below | 1–4 | setting default |
| 6 | `Snooze minutes [5]:` | 1–60 | setting default |
| 7 | `Max snoozes (0 = unlimited) [3]:` | 0–20 | 3 |
| 8 | Summary + `Save this alarm? [Y/n]:` | y/n | Y |

Repeat list:
```
 1. Once        2. Every day     3. Weekdays (Mon-Fri)
 4. Weekends    5. Custom days   0. Back
```
Option 5 asks `Days (e.g. mon,wed,fri):`.

Sound list:
```
 1. Default beep    2. Custom .wav file    3. Silent (visual only)    0. Back
```
Option 2 asks `Path to .wav file:` and checks the file exists.

Result: `Alarm saved: 07:30 "Gym" (weekdays) - next in 22h 16m (Wed 29 Oct 07:30)`

### 2. Edit alarm
1. Shows the alarm list (same as option 4, numbered) and asks `Edit which alarm [1-N, 0 = back]:`.
2. Offers a field menu so the user changes only what they need:
```
 Editing alarm 2: 07:30 "Gym" weekdays
 1. Time        2. Label       3. Repeat / date
 4. Sound       5. Snooze      6. Max snoozes
 7. Save & finish             0. Cancel (discard changes)
```
3. Picking a field re-uses the Add prompt for that field with the current value as the default. Menu repeats until `7` (save) or `0` (discard).

### 3. Delete alarm
1. Shows numbered list. Prompt: `Delete which? (e.g. 2 or 1,3 or "all", 0 = back):`
2. Confirmation: `Delete 2 alarm(s)? [y/N]:`

### 4. List alarms
```
 No.  ID      Time   Label     Repeat    State     Next
  1   a1b2c3  07:30  Gym       Weekdays  Enabled   Wed 29 Oct 07:30 (in 22h 16m)
  2   d4e5f6  22:00  Sleep     Daily     Disabled  -
  3   9f8e7d  14:00  Call mom  Once      Missed    -
```
Then sub-prompt: `Show: 1. Active only  2. All (incl. disabled/done) [1]:` — shown first so the default view stays short.

### 5. Enable / disable alarm
Shows numbered list with state; `Toggle which alarm(s)? (e.g. 2 or 1,3, 0 = back):` flips each selected alarm and prints the new state.

### 6. Set timer
| Prompt | Accepts | Default |
|--------|---------|---------|
| `Duration (e.g. 90s, 10m, 1h30m, 00:05:00):` | formats at left; bare number = minutes | required |
| `Label [Timer]:` | text | `Timer` |

Result: `Timer set for 10m - rings at 09:24:05`.

### 7. Start ring mode
Shows live countdown and key hints; checks for catch-up alarms (FR-25) first.
```
 Ring mode - watching 2 alarm(s).      [m] back to menu   [Ctrl+C] exit
 Next: Gym at 07:30 (in 02:14:09)
```
While ringing:
```
 *** ALARM 07:30 - Gym ***
 [s] snooze 5m (2 left)    [d] dismiss
```

### 8. Show next alarm
Prints the next alarm, trigger time and time remaining (or "No active alarms").

### 9. Live clock
Updating `HH:MM:SS` line with date; any key or Ctrl+C returns to menu.

### 10. History
Last 20 events (newest first): timestamp, alarm label, event (fired, snoozed, dismissed, missed). Prompt: `1. Show all 100  2. Clear history  0. Back`.

### 11. Settings
```
 1. Default snooze minutes      [5]
 2. Auto-stop ringing after (s) [60]
 3. Late-start grace (minutes)  [5]
 4. Default sound               [beep]
 5. Time display                [24h]   (toggles 24h / 12h)
 0. Back
```
Choosing a number prompts for the new value with the current as default.

### 12. Test sound
Plays the default sound for ~3 s and reports which backend was used (winsound / system player / terminal bell).

## 2.2 Package layout

```
python_cli_alarm/
├── pyproject.toml            # console script: alarm = alarm_cli.app:main
├── README.md
├── docs/SPEC.md
├── src/alarm_cli/
│   ├── __init__.py
│   ├── __main__.py           # python -m alarm_cli
│   ├── app.py                # main(): menu loop, dispatch table {number: handler}
│   ├── menu.py               # main menu rendering and number -> action mapping
│   ├── prompts.py            # ask_text, ask_choice, ask_yes_no, ask_time, ask_duration ... (re-prompt on invalid, Ctrl+C -> Cancelled)
│   ├── actions/              # one module per menu item: add, edit, delete, list_, toggle, timer, ring, next_, clock, history, settings, sound
│   ├── models.py             # Alarm, Settings, HistoryEvent dataclasses
│   ├── parsing.py            # parse_time, parse_duration, parse_repeat, parse_date (pure)
│   ├── scheduler.py          # next_trigger(), is_due() (pure)
│   ├── storage.py            # JsonStore: load/save atomic, mtime check, paths
│   ├── engine.py             # ring-mode loop: tick, fire, snooze, dismiss, reload
│   ├── ringer.py             # sound playback abstraction + backends
│   ├── keys.py               # non-blocking key reader (msvcrt / termios)
│   ├── render.py             # tables, countdown, header (rich optional)
│   ├── console.py            # IO protocol (input/print) so prompts are testable
│   ├── clock.py              # Clock protocol: SystemClock, FakeClock
│   └── errors.py             # AlarmError, ValidationError, Cancelled
└── tests/
```

## 2.3 Data model

`alarms.json`:
```json
{
  "version": 1,
  "alarms": [
    {
      "id": "a1b2c3",
      "time": "07:30:00",
      "date": null,
      "repeat": ["mon","tue","wed","thu","fri"],
      "label": "Gym",
      "sound": "beep",
      "snooze_minutes": 5,
      "max_snoozes": 3,
      "enabled": true,
      "kind": "alarm",
      "created_at": "2026-10-28T09:00:00+05:30",
      "last_fired_at": null,
      "state": "active"
    }
  ]
}
```
- `repeat`: empty list = one-time. `kind`: `alarm` | `timer` (timers store absolute `date` + `time`).
- `state`: `active` | `done` | `missed`.
- `settings.json` and `history.jsonl` (append-only, trimmed to 100) live beside it.
- Snooze state is runtime-only (held by the engine).
- Menu numbers are positions in the currently displayed list, sorted by next trigger time; they are never stored.

## 2.4 Core logic

- `scheduler.next_trigger(alarm, now) -> datetime | None`: pure function. One-time: stated date/time or next occurrence; recurring: first matching weekday ≥ now. Built from local wall-clock fields then localised (DST-safe: nonexistent times roll forward, ambiguous pick first).
- `app.main()`: `while True: render menu → ask_choice → handler(ctx)`; handlers raise `Cancelled` on Ctrl+C/back and the loop catches it and continues.
- `engine.run()` (ring mode, tick = 0.5 s):
  1. Reload store if mtime changed.
  2. Find due alarms: `trigger <= now`, not already fired for that occurrence, within grace.
  3. If due → ring: start sound thread, poll keys, handle snooze / dismiss / auto-stop.
  4. Persist `last_fired_at`/state, append history.
  5. If idle: render countdown, poll `m` for back to menu.
- De-duplication keyed on `(id, trigger_datetime)`.
- Ring state machine: `IDLE → RINGING → (SNOOZED → RINGING)* → DISMISSED | MISSED`.

## 2.5 Platform abstractions

| Concern | Windows | macOS/Linux | Fallback |
|---------|---------|-------------|----------|
| Sound (beep) | `winsound.Beep` | write `\a` | `\a` |
| Sound (wav) | `winsound.PlaySound` async | `afplay` / `aplay` / `paplay` via `subprocess` | `\a` |
| Keys (ring mode, clock) | `msvcrt.kbhit/getwch` | `termios` + `select` | line input |
| Prompts | `input()` | `input()` | — |

`Ringer`, `KeyReader`, and `Console` are tiny interfaces so tests inject fakes.

## 2.6 Error handling

- `ValidationError` inside a prompt → print message, re-ask. Never leaves the prompt.
- `Cancelled` (Ctrl+C or `0`) → back to the menu with "Cancelled." message.
- Storage: corrupt JSON → renamed to `.bak`, start empty, warn. Write failures → message and return to menu.
- Ctrl+C at the main menu prompt asks `Exit? [y/N]`; in ring mode/clock it returns to the menu and stops sound.
- Unexpected exception → one-line error, exit code 1 (full traceback only with `ALARM_CLI_DEBUG=1`).
- Concurrency: load → modify → atomic save per action; last writer wins (single-user).

## 2.7 Testing strategy

- Unit: `parsing`, `scheduler` (DST, month/year rollover, weekday sets), `storage` (atomic write, corrupt file) with `pytest` and `FakeClock`.
- Prompts: feed scripted input lists via a fake `Console`; verify defaults on Enter, re-prompt on invalid input, cancel handling.
- Menu flows: scripted sessions (e.g. `["1","07:30","Gym","3","","","","","y","0"]`) against `tmp_path` storage; assert saved JSON and printed output.
- Engine: drive `tick()` with FakeClock + FakeRinger + scripted keys: ring, snooze, max snoozes, auto-stop, grace window, hot reload, simultaneous alarms.
- Tooling: `ruff`, `mypy --strict` on `src/`, CI matrix (win/linux/mac × 3.10–3.13) if a repo is added.

---

# Part 3 — Step-by-Step Implementation Plan

### Phase 0 — Setup (0.5 day)
1. Create `src/alarm_cli` layout and `pyproject.toml` (`[project.scripts] alarm = "alarm_cli.app:main"`, dev extras: pytest, ruff, mypy).
2. `python -m venv .venv`, `pip install -e .[dev]`; confirm `alarm` launches a stub menu.
3. Add `errors.py`, `clock.py` (SystemClock + FakeClock), `console.py` (real + fake).

### Phase 1 — Pure core (1 day)
4. `models.py`: `Alarm`, `Settings`, `HistoryEvent` with `to_dict/from_dict` and validation.
5. `parsing.py`: time, duration, repeat, date parsers + parametrised tests.
6. `scheduler.py`: `next_trigger`, `is_due`, `format_remaining`; tests for rollover, weekdays, DST.

### Phase 2 — Persistence (0.5 day)
7. `storage.py`: path resolution (`ALARM_CLI_HOME`), atomic JSON read/write, versioning, corrupt-file backup, collision-checked 6-char hex IDs.
8. Settings store + history log (append and trim). Tests with `tmp_path`.

### Phase 3 — Menu framework & prompts (1 day)
9. `prompts.py`: `ask_text`, `ask_choice`, `ask_yes_no`, `ask_int`, `ask_time`, `ask_duration`, `ask_date`, `ask_days`, each with default handling, re-prompt, cancel. Tests with scripted console.
10. `menu.py` + `app.py`: header, numbered menu, dispatch table, `Cancelled` handling, exit confirmation.
11. `render.py`: alarm table (plain text first), header line, time-remaining formatting.

### Phase 4 — Menu actions (1.5 days)
12. Implement options **1 Add**, **4 List**, **3 Delete** (list-number selection, `1,3`/`all`, confirm).
13. Implement **5 Enable/disable**, **2 Edit** (field submenu), **6 Timer**, **8 Next**.
14. Implement **11 Settings** and **10 History**.
15. Scripted-session tests for every action.
   **Milestone: fully usable alarm manager (no ringing yet).**

### Phase 5 — Ringing engine (1.5 days)
16. Spike first: non-blocking key polling alongside `winsound`, on Windows then POSIX.
17. `ringer.py` (`BeepRinger`, `WavRinger`, `NullRinger`) and **12 Test sound**.
18. `keys.py`: msvcrt / termios readers + fake.
19. `engine.py`: tick, due detection, dedupe, state machine (ring/snooze/dismiss/auto-stop), recurring recompute, one-time completion.
20. **7 Ring mode** action: countdown render, `m` to return to menu, Ctrl+C handling.
21. Engine tests for FR-20 … FR-26.
   **Milestone: end-to-end alarm rings, snoozes, dismisses.**

### Phase 6 — Robustness (1 day)
22. Hot reload by mtime; grace-window catch-up; missed handling shown in list.
23. Simultaneous-alarm prompt; max snoozes.
24. DST edge cases; system sleep/resume (large clock jump → catch-up, not a burst of rings).

### Phase 7 — Polish & packaging (1 day)
25. **9 Live clock**; optional `rich` rendering with fallback; 12h/24h display; colour only when `isatty()` and `NO_COLOR` unset; screens fit 80×24.
26. `mypy --strict`, `ruff` clean, coverage ≥ 85% on scheduler/engine.
27. README: install, quick start with a menu walkthrough, ring-mode explanation, tips for auto-starting (Task Scheduler / systemd / launchd). Manual test checklist on Windows plus POSIX smoke test; tag `v0.1.0`.

### Highest risks
Cross-platform key polling + sound while ringing (steps 16–20) and clock jumps (step 24). Spike step 16 before building the engine.

### Definition of done
All FRs implemented or explicitly deferred in the README; acceptance examples in §1.6 pass; tests green on Windows and one POSIX OS; `pip install .` yields a working `alarm` command that opens the menu.

---

# Open decisions (defaults chosen; change if you disagree)

| Topic | Default chosen | Alternative |
|-------|----------------|-------------|
| Menu library | Plain `input()` / `print()` | `questionary` / `rich.prompt` (nicer UX, extra dependency) |
| Ringing while in menu | Separate Ring mode (option 7) | Ring in a background thread during the menu (interrupts prompts, more complex) |
| Snooze persistence | Runtime only | Persist so a restart keeps snoozes |
| Alarm selection | By list number | By ID |
