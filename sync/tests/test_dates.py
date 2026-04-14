import datetime as dt

import pytest

from r2_sync import dates_in_window


def test_basic_three_days():
    assert dates_in_window(3, now=dt.date(2026, 4, 13)) == [
        "2026-04-13",
        "2026-04-12",
        "2026-04-11",
    ]


def test_single_day():
    assert dates_in_window(1, now=dt.date(2026, 4, 13)) == ["2026-04-13"]


def test_spans_month_boundary():
    assert dates_in_window(3, now=dt.date(2026, 3, 1)) == [
        "2026-03-01",
        "2026-02-28",
        "2026-02-27",
    ]


def test_leap_year_boundary():
    assert dates_in_window(3, now=dt.date(2024, 3, 1)) == [
        "2024-03-01",
        "2024-02-29",
        "2024-02-28",
    ]


def test_today_first_ordering():
    result = dates_in_window(7, now=dt.date(2026, 4, 13))
    assert result[0] == "2026-04-13"
    assert result[-1] == "2026-04-07"
    assert len(result) == 7


def test_zero_days_rejected():
    with pytest.raises(ValueError):
        dates_in_window(0)


def test_negative_days_rejected():
    with pytest.raises(ValueError):
        dates_in_window(-1)


def test_default_now_is_utc_today():
    result = dates_in_window(1)
    today_utc = dt.datetime.now(dt.timezone.utc).date().isoformat()
    assert result == [today_utc]
