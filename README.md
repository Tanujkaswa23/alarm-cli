# alarm-cli

Menu-driven command-line alarm clock. No GUI, no database; data lives in JSON files
(`%APPDATA%\alarm-cli` on Windows, override with `ALARM_CLI_HOME`).

    pip install -e .[dev]
    alarm            # or: python -m alarm_cli

Pick options by number. Alarms only ring while **Ring mode** (option 7) is running;
press `m` there to return to the menu. While ringing: `s` snooze, `d`/Enter dismiss.

Run tests: `python -m pytest`. Design: [docs/SPEC.md](docs/SPEC.md).
