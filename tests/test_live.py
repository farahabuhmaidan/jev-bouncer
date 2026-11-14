"""SQLite store, seeding from the committed model outputs, and live event processing (design/14)."""
import pytest

from server.db import Store, seed_store
from server.live import process_event

BLOCKER = {"needs_sanad": 0.9, "time_sensitive": 0.9, "wording_only_urgency": 0.05, "family_matter": 0.02,
           "blocks_release": 0.93, "is_noise": 0.02}
LOUD = {**BLOCKER, "blocks_release": 0.05, "wording_only_urgency": 0.93, "time_sensitive": 0.4}


def fake_ask(answers, calls=None, fail=0):
    state = {"n": 0}

    def ask(st, etype):
        state["n"] += 1
        if calls is not None:
            calls.append(st)
        if state["n"] <= fail:
            return {"answers": {}, "latency_ms": 5, "usage": {}, "request": {}, "error": "HTTP 500"}
        return {"answers": answers, "latency_ms": 5, "usage": {"cost": 1e-5}, "request": {"state": st}, "error": None}
    return ask


sync = lambda f: f()  # noqa: E731  run the LLM writer inline in tests


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.db")
    seed_store(s)
    return s


def test_seed_loads_33_events_with_results(store):
    events = store.all_events()
    assert len(events) == 33 and all(e["origin"] == "seed" for e in events)
    assert set(store.results()) == {e["id"] for e in events}
    assert store.get("clock") == "08:00" and store.get("snapshot")["people"]["rami"]["name"] == "Rami"


def test_live_event_gets_id_time_and_decision(store):
    store.put("clock", "14:12")
    out = process_event(store, {"type": "message", "source": "compose", "sender": "rami", "text": "checkout is broken"},
                        ask=fake_ask(BLOCKER), write=None)
    assert out["event"]["id"] == "live-1" and out["event"]["time"] == "14:12" and out["event"]["origin"] == "live"
    assert out["decision"]["action"] == "interrupt" and out["decision"]["rule"] == 4
    assert out["result"]["state"]["message"] == "checkout is broken"
    assert len(store.all_events()) == 34


def test_live_jev_error_is_stored_as_error_after_one_retry(store):
    calls = []
    out = process_event(store, {"type": "message", "source": "compose", "sender": "rami", "text": "hi"},
                        ask=fake_ask(BLOCKER, calls, fail=2), write=None)
    assert len(calls) == 2 and out["decision"]["action"] == "error"
    assert store.results()[out["event"]["id"]]["jev"]["error"] == "HTTP 500"


def test_live_retry_recovers(store):
    out = process_event(store, {"type": "message", "source": "compose", "sender": "rami", "text": "hi"},
                        ask=fake_ask(BLOCKER, fail=1), write=None)
    assert out["decision"]["action"] == "interrupt"


def test_live_same_minute_orders_by_id(store):
    store.put("clock", "14:20")  # evt-015 is at 14:20 too
    out = process_event(store, {"type": "message", "source": "compose", "sender": "rami", "text": "x"},
                        ask=fake_ask(BLOCKER), write=None)
    ids = [e["id"] for e in sorted(store.all_events(), key=lambda e: (e["time"], e["id"])) if e["time"] == "14:20"]
    assert ids == ["evt-015", out["event"]["id"]]


def test_auto_reply_written_for_batched_person(store):
    store.put("clock", "14:06")
    seen = {}

    def reply(state, slot):
        seen["slot"] = slot
        return f"Sanad will reply at {slot}."
    out = process_event(store, {"type": "message", "source": "compose", "sender": "layla", "text": "URGENT!!! font"},
                        ask=fake_ask(LOUD), run=sync, reply=reply, explain=lambda s: None)
    assert out["decision"]["action"] == "batch"
    assert store.results()[out["event"]["id"]]["auto_reply"] == "Sanad will reply at 16:00."


def test_no_auto_reply_when_interrupting(store):
    out = process_event(store, {"type": "message", "source": "compose", "sender": "rami", "text": "broken"},
                        ask=fake_ask(BLOCKER), run=sync, reply=lambda s, t: pytest.fail("no reply"), explain=lambda s: None)
    assert store.results()[out["event"]["id"]]["auto_reply"] is None


def test_writer_failure_recorded_not_raised(store):
    def boom(state, slot):
        raise RuntimeError("LLM down")
    out = process_event(store, {"type": "message", "source": "compose", "sender": "layla", "text": "URGENT!!!"},
                        ask=fake_ask(LOUD), run=sync, reply=boom, explain=lambda s: None)
    r = store.results()[out["event"]["id"]]
    assert r["auto_reply"] is None and "LLM down" in r["llm_error"] and r["writing"] is False


def test_reset_live_keeps_seed(store):
    process_event(store, {"type": "message", "source": "compose", "sender": "rami", "text": "x"}, ask=fake_ask(BLOCKER), write=None)
    store.add_feedback("evt-020", "ask", "interrupt")
    store.put("clock", "15:00")
    store.reset_live()
    assert len(store.all_events()) == 33 and store.feedback() == {} and store.get("clock") == "08:00"
    assert "live-1" not in store.results()


def test_live_ids_keep_counting_after_restart(tmp_path):
    s = Store(tmp_path / "t.db"); seed_store(s)
    process_event(s, {"type": "message", "source": "compose", "sender": "rami", "text": "x"}, ask=fake_ask(BLOCKER), write=None)
    s2 = Store(tmp_path / "t.db")
    out = process_event(s2, {"type": "message", "source": "compose", "sender": "rami", "text": "y"}, ask=fake_ask(BLOCKER), write=None)
    assert out["event"]["id"] == "live-2"
