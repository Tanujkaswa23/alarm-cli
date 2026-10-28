from datetime import time, timedelta

import pytest

from alarm_cli.errors import ValidationError
from alarm_cli.parsing import (
    describe_repeat, format_remaining, format_time, parse_date, parse_days, parse_duration, parse_time,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("07:30", time(7, 30)), ("7:30", time(7, 30)), ("23:59:59", time(23, 59, 59)),
        ("7:30 PM", time(19, 30)), ("7:30pm", time(19, 30)), ("12:00 AM", time(0, 0)),
        ("12:15 pm", time(12, 15)), ("7pm", time(19, 0)),
    ],
)
def test_parse_time_valid(text, expected):
    assert parse_time(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "25:00", "07:60", "7", "13:00 PM", "0:30 AM", "7:30:99"])
def test_parse_time_invalid(text):
    with pytest.raises(ValidationError):
        parse_time(text)


@pytest.mark.parametrize(
    "text,seconds",
    [("90s", 90), ("10m", 600), ("1h30m", 5400), ("00:05:00", 300), ("5", 300), ("1h 2m 3s", 3723)],
)
def test_parse_duration_valid(text, seconds):
    assert parse_duration(text) == timedelta(seconds=seconds)


@pytest.mark.parametrize("text", ["", "0", "0s", "abc", "25h", "00:99:00", "10x"])
def test_parse_duration_invalid(text):
    with pytest.raises(ValidationError):
        parse_duration(text)


def test_parse_days():
    assert parse_days("fri, mon wednesday") == ["mon", "wed", "fri"]
    with pytest.raises(ValidationError):
        parse_days("mon,funday")
    with pytest.raises(ValidationError):
        parse_days("  ")


def test_parse_date():
    assert parse_date("2026-12-25").day == 25
    with pytest.raises(ValidationError):
        parse_date("25/12/2026")


def test_formatting():
    assert format_time(time(19, 5), "12h") == "7:05 PM"
    assert format_time(time(19, 5), "24h") == "19:05"
    assert format_remaining(timedelta(hours=22, minutes=16)) == "22h 16m"
    assert format_remaining(timedelta(seconds=45)) == "45s"
    assert describe_repeat(["mon", "tue", "wed", "thu", "fri"]) == "Weekdays"
    assert describe_repeat([]) == "Once"
