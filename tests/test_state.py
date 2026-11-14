from pathlib import Path

import pytest

from pipeline.load import load_events, load_snapshot
from pipeline.state import build_state, next_free_slot

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def snap():
    return load_snapshot(DATA / "snapshot.json")


@pytest.fixture(scope="module")
def events(snap):
    return {e["id"]: e for e in load_events(DATA / "events.json", snap)}


def test_rami_state(snap, events):
    s = build_state(events["evt-015"], snap)
    assert set(s) == {"now", "sanad", "today", "sender", "channel", "message", "linked_items"}
    assert "focus block until 16:00" in s["now"]
    assert s["sender"] == "Rami, Junior developer (Sanad's team: checkout)"
    assert s["linked_items"][0].startswith("CHK-88")


def test_ci_state_has_ci_not_message(snap, events):
    s = build_state(events["evt-018"], snap)
    assert "message" not in s
    assert s["ci"]["branch"] == "investor-demo" and "test_discounted_plan_total" in s["ci"]["log_tail"]
    assert any(i.startswith("PR #212") for i in s["linked_items"])


def test_ci_state_reads_log_file(snap, events):
    s = build_state(events["evt-016"], snap)
    assert "Timed out" in s["ci"]["log_tail"]


def test_unknown_sender(snap):
    ev = {"id": "x", "time": "10:00", "type": "message", "source": "slack", "sender": "unknown:U0NOBODY", "text": "hi"}
    assert build_state(ev, snap)["sender"] == "Unknown sender (U0NOBODY)"


def test_no_links_omits_linked_items(snap, events):
    assert "linked_items" not in build_state(events["evt-010"], snap)


def test_no_budget_in_state(snap, events):
    text = str(build_state(events["evt-015"], snap)).lower()
    assert "budget" not in text and "interrupt" not in text


def test_bulk_mail_fact(snap, events):
    assert "unsubscribe" in build_state(events["evt-001"], snap)["mail_type"].lower()


def test_evening_now(snap, events):
    assert "after work hours" in build_state(events["evt-030"], snap)["now"]


@pytest.mark.parametrize("t,expected", [("14:20", "16:00"), ("12:00", "12:30"), ("19:10", "09:00 tomorrow"),
                                        ("17:40", "09:00 tomorrow"), ("09:35", "09:45")])
def test_next_free_slot(snap, t, expected):
    assert next_free_slot(t, snap) == expected
