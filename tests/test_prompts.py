from datetime import time

import pytest

from alarm_cli import prompts
from alarm_cli.console import FakeConsole
from alarm_cli.errors import Cancelled


def test_default_on_enter():
    c = FakeConsole([""])
    assert prompts.ask_text(c, "Label", "Alarm") == "Alarm"


def test_reprompts_on_invalid_time():
    c = FakeConsole(["abc", "25:00", "7:30 PM"])
    assert prompts.ask_time(c, "Time") == time(19, 30)
    assert c.text.count("Invalid time") == 2


def test_required_value():
    c = FakeConsole(["", "10"])
    assert prompts.ask_int(c, "Num", 1, 20) == 10
    assert "A value is required." in c.text


def test_int_bounds():
    c = FakeConsole(["0", "99", "x", "5"])
    assert prompts.ask_int(c, "Snooze", 1, 60) == 5


def test_choice_default_and_cancel():
    assert prompts.ask_choice(FakeConsole([""]), ["a", "b"], default=2) == 1
    with pytest.raises(Cancelled):
        prompts.ask_choice(FakeConsole(["0"]), ["a", "b"])
    c = FakeConsole(["9", "1"])
    assert prompts.ask_choice(c, ["a", "b"], default=None) == 0


def test_yes_no():
    assert prompts.ask_yes_no(FakeConsole([""]), "?", True) is True
    assert prompts.ask_yes_no(FakeConsole([""]), "?", False) is False
    assert prompts.ask_yes_no(FakeConsole(["maybe", "Y"]), "?", False) is True


def test_selection():
    assert prompts.ask_selection(FakeConsole(["1, 3"]), "p", 3) == [0, 2]
    assert prompts.ask_selection(FakeConsole(["all"]), "p", 3) == [0, 1, 2]
    assert prompts.ask_selection(FakeConsole(["4", "2"]), "p", 3) == [1]
    assert prompts.ask_selection(FakeConsole(["1,2", "2"]), "p", 3, multi=False) == [1]
    with pytest.raises(Cancelled):
        prompts.ask_selection(FakeConsole(["0"]), "p", 3)


def test_eof_and_ctrl_c_cancel():
    with pytest.raises(Cancelled):
        prompts.ask_text(FakeConsole([]), "Label")

    class Interrupting(FakeConsole):
        def input(self, prompt=""):
            raise KeyboardInterrupt

    with pytest.raises(Cancelled):
        prompts.ask_text(Interrupting(), "Label")


def test_optional_date_validation():
    from alarm_cli.errors import ValidationError

    def reject(d):
        raise ValidationError("past")

    c = FakeConsole(["2020-01-01", ""])
    assert prompts.ask_optional_date(c, "Date", None, reject) is None
    assert "past" in c.text
