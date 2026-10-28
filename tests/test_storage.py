from datetime import time

from alarm_cli.models import Alarm, HistoryEvent, Settings
from alarm_cli.storage import HISTORY_LIMIT, JsonStore


def sample(i="a1b2c3"):
    return Alarm(id=i, time=time(7, 30), label="Gym", repeat=["mon"], created_at="2026-10-28T09:00:00+00:00")


def test_roundtrip(tmp_path):
    store = JsonStore(tmp_path)
    store.save_alarms([sample()])
    loaded = store.load_alarms()
    assert loaded == [sample()]
    assert not list(tmp_path.glob("*.tmp"))


def test_missing_files_give_defaults(tmp_path):
    store = JsonStore(tmp_path)
    assert store.load_alarms() == []
    assert store.load_settings() == Settings()
    assert store.load_history() == []


def test_corrupt_file_backed_up(tmp_path):
    warnings = []
    store = JsonStore(tmp_path, warn=warnings.append)
    store.home.mkdir(exist_ok=True)
    store.alarms_path.write_text("{not json", encoding="utf-8")
    assert store.load_alarms() == []
    assert (tmp_path / "alarms.json.bak").exists()
    assert warnings


def test_settings_validation(tmp_path):
    store = JsonStore(tmp_path)
    (tmp_path / "settings.json").write_text('{"snooze_minutes": "bad", "time_format": "99h", "grace_minutes": 9}')
    s = store.load_settings()
    assert s.snooze_minutes == 5 and s.time_format == "24h" and s.grace_minutes == 9


def test_history_trimmed(tmp_path):
    store = JsonStore(tmp_path)
    for i in range(HISTORY_LIMIT + 5):
        store.append_history(HistoryEvent("2026-10-28T09:00:00+00:00", "x", f"l{i}", "fired"))
    events = store.load_history()
    assert len(events) == HISTORY_LIMIT and events[-1].label == f"l{HISTORY_LIMIT + 4}"
    store.clear_history()
    assert store.load_history() == []


def test_update_alarm_and_ids(tmp_path):
    store = JsonStore(tmp_path)
    store.save_alarms([sample("aaaaaa"), sample("bbbbbb")])
    store.update_alarm("bbbbbb", lambda a: setattr(a, "label", "changed"))
    assert [a.label for a in store.load_alarms()] == ["Gym", "changed"]
    assert store.new_id(store.load_alarms()) not in {"aaaaaa", "bbbbbb"}
