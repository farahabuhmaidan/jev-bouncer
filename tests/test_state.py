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


# --- deadline fact and commitments (design/02, teammate update 6fdb305) ---
from pipeline.state import deadline_minutes  # noqa: E402


def _msg(text, time="14:00", sender="noor"):
    return {"id": "x", "time": time, "type": "message", "source": "slack", "sender": sender, "text": text}


def test_deadline_by_and_before_hhmm(snap):
    assert deadline_minutes(_msg("please confirm by 14:40"), snap) == 40
    assert deadline_minutes(_msg("we need it live before 15:00 for our launch"), snap) == 60


def test_deadline_today_ends_at_18(snap):
    assert deadline_minutes(_msg("can you look at this today?"), snap) == 240


def test_deadline_linked_ticket_due_today(snap, events):
    assert deadline_minutes(events["evt-015"], snap) == 220  # Rami 14:20, CHK-88 due today → 18:00


def test_deadline_none_when_nothing_matches_or_passed(snap):
    assert deadline_minutes(_msg("lunch?"), snap) is None
    assert deadline_minutes(_msg("please confirm by 13:00"), snap) is None


def test_deadline_takes_the_nearest(snap):
    assert deadline_minutes(_msg("by 17:00 at the latest, ideally before 14:30, today"), snap) == 30


def test_deadline_not_in_state(snap):
    s = build_state(_msg("please confirm by 14:40"), snap)
    assert "deadline" not in str(s).lower() or "by 14:40" in s["message"]
    assert "deadline_in_minutes" not in s


def test_commitment_for_matching_sender(snap, events):
    assert build_state(events["evt-014"], snap)["commitment"] == "Sanad told the CEO the deck was final yesterday"


def test_no_commitment_otherwise(snap, events):
    assert "commitment" not in build_state(events["evt-015"], snap)


def test_customer_sender_sentence():
    snap = load_snapshot(DATA / "snapshot.json")
    assert build_state(_msg("hi", sender="hadi"), snap)["sender"] == "Hadi, Operations lead at Cedar Market (customer)"


def test_commitment_only_when_about_matches(snap):
    roadmap = _msg("thinking about next quarter's roadmap, thoughts on moving subscriptions up?", sender="layla")
    assert "commitment" not in build_state(roadmap, snap)


def test_deadline_tonight_is_not_a_workday_deadline(snap):
    assert deadline_minutes(_msg("early-bird tickets end tonight!", time="16:50"), snap) is None
