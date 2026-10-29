import pytest

from datamate.formatter import AnswerFormatter


def test_format_number_currency() -> None:
    assert AnswerFormatter.format_number("4,820,000", is_currency=True) == 4820000
    assert AnswerFormatter.format_number(4820000.0, is_currency=True) == 4820000
    assert AnswerFormatter.format_number(18.0) == 18


def test_format_number_decimal() -> None:
    assert AnswerFormatter.format_number(18.666) == 18.67
    assert AnswerFormatter.format_number("123.456") == 123.46


def test_format_percent() -> None:
    assert AnswerFormatter.format_percent("12.4%") == 12.4
    assert AnswerFormatter.format_percent("-5.276%") == -5.28
    assert AnswerFormatter.format_percent(10.5) == 10.5


def test_format_date() -> None:
    assert AnswerFormatter.format_date("2026-08-15T00:00:00") == "2026-08-15"
    assert AnswerFormatter.format_date("2025-09") == "2025-09"


def test_format_boolean() -> None:
    assert AnswerFormatter.format_boolean("True") is True
    assert AnswerFormatter.format_boolean("đúng") is True
    assert AnswerFormatter.format_boolean("sai") is False
    assert AnswerFormatter.format_boolean(False) is False


def test_format_list() -> None:
    formatted = AnswerFormatter.format_list([" Cà phê sữa ", 10.0, "Bạc xỉu"])
    assert formatted == ["Cà phê sữa", 10, "Bạc xỉu"]


def test_format_table() -> None:
    raw_table = {
        "columns": [" khach_hang ", "so_tien_no"],
        "rows": [[" Chị Lan ", 3200000.0]],
    }
    formatted = AnswerFormatter.format_table(raw_table)
    assert formatted == {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [["Chị Lan", 3200000]],
    }


def test_format_abstain_and_unanswerable() -> None:
    assert AnswerFormatter.format_answer("abstain", "anything") is None
    assert AnswerFormatter.format_answer("unanswerable", "anything") is None


def test_format_number_invalid() -> None:
    with pytest.raises(ValueError):
        AnswerFormatter.format_number("invalid_number")

