"""HTTP API (design/14-app.md § API), with fake model calls."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.db import Store, seed_store

ROOT = Path(__file__).resolve().parent.parent
BLOCKER = {"needs_sanad": 0.9, "time_sensitive": 0.9, "wording_only_urgency": 0.05, "family_matter": 0.02,
           "blocks_release": 0.93, "is_noise": 0.02}


def ask_ok(state, etype):
    return {"answers": BLOCKER, "latency_ms": 5, "usage": {}, "request": {}, "error": None}


def ask_down(state, etype):
    return {"answers": {}, "latency_ms": 5, "usage": {}, "request": {}, "error": "HTTP 503"}


def ask_no_key(state, etype):
    raise KeyError("OPENROUTER_API_KEY")


@pytest.fixture
def make(tmp_path):
    def _make(ask=ask_ok):
        store = Store(tmp_path / "t.db")
        seed_store(store)
        return TestClient(create_app(store, ask=ask, write=False)), store
    return _make


def test_day_hides_future_events(make):
    c, _ = make()
    c.post("/api/clock", json={"time": "09:00"})
    day = c.get("/api/day").json()
    assert day["clock"] == "09:00" and [e["id"] for e in day["events"]] == ["evt-003", "evt-002", "evt-001"]
    assert day["events"][0]["decision"]["action"] and "state" in day["events"][0]["result"]


def test_clock_rejects_bad_time(make):
    c, _ = make()
    assert c.post("/api/clock", json={"time": "25:00"}).status_code == 422


def interrupts(c):
    return sum(e["decision"]["action"] == "interrupt" for e in c.get("/api/day").json()["events"])


def test_settings_put_reroutes(make):
    c, _ = make()
    c.post("/api/clock", json={"time": "20:00"})
    before = interrupts(c)
    s = c.put("/api/settings", json={"interruptBar": 0.95, "risingBar": False, "budget": 1}).json()
    assert s["budget"] == 1 and interrupts(c) < before
    assert c.get("/api/day").json()["budget"]["total"] == 1


def test_settings_put_bad_values_fall_back(make):
    c, _ = make()
    s = c.put("/api/settings", json={"eveningStart": "", "family": "x", "budget": -3}).json()
    assert s["eveningStart"] == "18:00" and s["family"] == ["maha", "school"] and s["budget"] == 5


def test_post_event_live(make):
    c, _ = make()
    c.post("/api/clock", json={"time": "14:12"})
    r = c.post("/api/events", json={"sender": "rami", "text": "checkout shows 0 JOD"})
    assert r.status_code == 201
    body = r.json()
    assert body["event"]["id"] == "live-1" and body["decision"]["action"] == "interrupt"
    day = c.get("/api/day").json()
    assert day["events"][0]["id"] == "live-1" and "live-1" in day["phone"]


def test_post_event_unknown_sender_422(make):
    c, store = make()
    assert c.post("/api/events", json={"sender": "nobody", "text": "hi"}).status_code == 422
    assert len(store.all_events()) == 33


def test_post_event_empty_text_422(make):
    c, store = make()
    assert c.post("/api/events", json={"sender": "rami", "text": "   "}).status_code == 422
    assert len(store.all_events()) == 33


def test_post_event_jev_down_502_and_stored(make):
    c, store = make(ask=ask_down)
    r = c.post("/api/events", json={"sender": "rami", "text": "hello"})
    assert r.status_code == 502 and r.json()["decision"]["action"] == "error"
    assert len(store.all_events()) == 34


def test_post_event_without_key_is_clear_error(make):
    c, _ = make(ask=ask_no_key)
    r = c.post("/api/events", json={"sender": "rami", "text": "hello"})
    assert r.status_code == 502 and "OPENROUTER_API_KEY" in r.json()["result"]["jev"]["error"]


def test_ingest_slack_raw_uses_adapter(make):
    c, _ = make()
    raw = json.loads((ROOT / "data" / "raw" / "slack" / "rami-dm.json").read_text())
    r = c.post("/api/ingest/slack", json=raw)
    assert r.status_code == 201 and r.json()["event"]["sender"] == "rami" and r.json()["event"]["source"] == "slack"


def test_ingest_unknown_source_404(make):
    c, _ = make()
    assert c.post("/api/ingest/fax", json={}).status_code == 404


def test_ingest_bad_payload_422(make):
    c, _ = make()
    assert c.post("/api/ingest/slack", json={"nope": 1}).status_code == 422


def test_feedback_ask_never_changes_metrics(make):
    c, _ = make()
    before = c.get("/api/metrics").json()
    assert c.post("/api/events/evt-020/feedback", json={"kind": "ask", "choice": "interrupt"}).status_code == 201
    assert c.get("/api/metrics").json() == before
    c.post("/api/clock", json={"time": "16:00"})
    e = next(e for e in c.get("/api/day").json()["events"] if e["id"] == "evt-020")
    assert e["feedback"][0]["value"] == "interrupt"


def test_feedback_urgent_puts_event_on_phone(make):
    c, _ = make()
    c.post("/api/clock", json={"time": "15:00"})
    c.post("/api/events/evt-014/feedback", json={"kind": "urgent"})
    assert "evt-014" in c.get("/api/day").json()["phone"]


def test_feedback_validation(make):
    c, _ = make()
    assert c.post("/api/events/nope/feedback", json={"kind": "urgent"}).status_code == 404
    assert c.post("/api/events/evt-020/feedback", json={"kind": "ask", "choice": "explode"}).status_code == 422


def test_metrics_shape(make):
    c, _ = make()
    m = c.get("/api/metrics").json()
    assert round(m["jev"]["accuracy"] * 100) == 64 and m["n"] == 33 and m["settings_changed"] is False


def test_metrics_ignore_live_events(make):
    c, _ = make()
    before = c.get("/api/metrics").json()
    c.post("/api/events", json={"sender": "rami", "text": "x"})
    assert c.get("/api/metrics").json()["jev"]["accuracy"] == before["jev"]["accuracy"]


def test_digest_only_batched(make):
    c, _ = make()
    c.post("/api/clock", json={"time": "20:00"})
    batched = {e["id"] for e in c.get("/api/day").json()["events"] if e["decision"]["action"] == "batch"}
    ids = {i["event_id"] for g in c.get("/api/digest").json()["groups"] for i in g["items"]}
    assert ids and ids <= batched


def test_people_and_event_detail(make):
    c, _ = make()
    assert any(p["key"] == "rami" for p in c.get("/api/people").json())
    assert c.get("/api/events/evt-015").json()["decision"]["rule"] == 4
    assert c.get("/api/events/nope").status_code == 404


def test_reset(make):
    c, store = make()
    c.post("/api/events", json={"sender": "rami", "text": "x"})
    c.post("/api/clock", json={"time": "15:00"})
    assert c.post("/api/reset").status_code == 200
    assert len(store.all_events()) == 33 and c.get("/api/day").json()["clock"] == "08:00"


def test_moments_in_time_order(make):
    c, _ = make()
    m = c.get("/api/moments").json()
    assert [x["name"] for x in m] == ["loud-vs-quiet", "ci-trio", "unsure", "evening"] and m[0]["time"] == "14:05"
