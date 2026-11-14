"""Code reads when a message's task is due (no model): the reminder date and time."""
from datetime import date

from pipeline.when import resolve_when

TODAY = date(2026, 11, 14)  # Saturday


def w(text, now="14:00"):
    return resolve_when(text, TODAY, now)


def test_next_month_is_the_first_at_nine():
    assert w("you need to pay school fees next month") == {"date": "2026-12-01", "time": "09:00", "phrase": "next month"}


def test_tomorrow_with_time():
    assert w("dentist tomorrow at 4pm") == {"date": "2026-11-15", "time": "16:00", "phrase": "tomorrow at 4pm"}


def test_weekday_is_the_next_one():
    assert w("renew the car insurance on Monday")["date"] == "2026-11-16"
    assert w("call the bank on saturday")["date"] == "2026-11-21"


def test_next_week_is_monday():
    assert w("send the report next week")["date"] == "2026-11-16"


def test_in_n_days():
    assert w("pay rent in 3 days")["date"] == "2026-11-17"


def test_explicit_date():
    assert w("the visa appointment is on 3 December")["date"] == "2026-12-03"
    assert w("fees due Dec 20")["date"] == "2026-12-20"


def test_nothing_or_only_today_times():
    assert w("lunch?") is None
    assert w("please confirm by 14:40") is None
