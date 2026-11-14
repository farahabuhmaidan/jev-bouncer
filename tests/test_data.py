"""Checks on the hand-made demo day (design/06-data.md)."""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
ACTIONS = {"interrupt", "batch", "delegate", "drop"}
MOMENTS = {"loud-vs-quiet", "ci-trio", "unsure", "evening"}


def _events():
    return json.loads((DATA / "events.json").read_text())


def _snapshot():
    return json.loads((DATA / "snapshot.json").read_text())


def _unified(events):
    """Events already in unified form (raw entries are checked by the adapter tests)."""
    return [e for e in events if "raw_source" not in e]


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
    )
    assert n <= 5


def test_ci_events_have_logs_and_failure_type():
    for e in _unified(_events()):
        if e["type"] == "ci_failure":
            assert (DATA / e["log_file"]).is_file(), e["id"]
            assert e["label"]["failure_type"] in {"flaky_test", "code_regression", "infra_problem", "config_or_lint"}
