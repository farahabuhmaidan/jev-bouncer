"""Checks on the hand-made demo day (design/06-data.md)."""
import json
import re
from pathlib import Path

from pipeline.load import load_events, load_snapshot
from pipeline.state import deadline_minutes

DATA = Path(__file__).resolve().parent.parent / "data"
ACTIONS = {"interrupt", "batch", "delegate", "drop"}
MOMENTS = {"loud-vs-quiet", "ci-trio", "unsure", "evening"}


def _snapshot():
    return load_snapshot(DATA / "snapshot.json")


def _events():
    """Every event, raw entries already run through their adapters."""
    return load_events(DATA / "events.json", _snapshot())


def _unified(events):
    return events


def test_every_event_labelled():
    for e in _events():
        assert e["label"]["action"] in ACTIONS, e.get("id")


def test_ids_unique():
    ids = [e.get("id") for e in _unified(_events())]
    assert len(ids) == len(set(ids))


def test_times_are_hh_mm_in_day():
    for e in _unified(_events()):
        assert re.fullmatch(r"\d\d:\d\d", e["time"]), e["id"]
        assert "08:00" <= e["time"] <= "20:00", e["id"]


def test_calendar_comes_from_adapter():
    kinds = {c["title"]: c["kind"] for c in _snapshot()["calendar"]}
    assert kinds == {"Standup": "meeting", "Investor demo prep with the CEO": "meeting",
                     "Focus block": "focus", "School pickup": "personal"}


def test_senders_exist():
    people = _snapshot()["people"]
    for e in _unified(_events()):
        assert e["sender"] in people, (e["id"], e["sender"])


def test_demo_moments_present():
    found = {e.get("demo_moment") for e in _events()}
    assert MOMENTS <= found


def test_demo_events_not_holdout():
    for e in _events():
        if e.get("demo_moment"):
            assert not e.get("holdout"), e.get("id")


def test_holdout_count():
    assert sum(1 for e in _events() if e.get("holdout")) == 8


def test_budget_interrupts_at_most_5():
    people = _snapshot()["people"]
    n = sum(
        1
        for e in _unified(_events())
        if e["type"] == "message"
        and e["label"]["action"] == "interrupt"
        and e["time"] < "18:00"
        and people[e["sender"]]["relationship"] != "family"
        and not (deadline_minutes(e, _snapshot()) or 999) < 120  # the deadline row spends no budget
    )
    assert n <= 5


def test_ci_events_have_logs_and_failure_type():
    for e in _unified(_events()):
        if e["type"] == "ci_failure":
            assert e.get("log_tail") or (DATA / e["log_file"]).is_file(), e["id"]
            assert e["label"]["failure_type"] in {"flaky_test", "code_regression", "infra_problem", "config_or_lint"}


def test_customer_deadline_email_is_raw_gmail_with_a_parseable_deadline():
    from pipeline.state import deadline_minutes
    entry = next(e for e in json.loads((DATA / "events.json").read_text()) if e["id"] == "evt-034")
    assert entry["raw_source"] == "gmail" and entry["label"]["action"] == "interrupt"
    e = next(e for e in _events() if e["id"] == "evt-034")
    assert e["sender"] == "hadi" and "08:00" < e["time"] < "18:00"
    assert deadline_minutes(e, _snapshot()) < 120
