"""Tests for shared utils."""

from datetime import datetime

from shared.utils import get_timer, is_date, start_timer


def test_start_timer() -> None:
    t = start_timer()
    assert isinstance(t, datetime)


def test_get_timer() -> None:
    t = start_timer()
    s = get_timer(t)
    assert isinstance(s, str)
    assert "0" in s or "0:00" in s


def test_is_date() -> None:
    assert is_date("2025-01-17") is True
    assert is_date("01/17/2025") is True
    assert is_date("not a date") is False
    assert is_date("") is False
