"""HTTP API (design/14-app.md § API), with fake model calls."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.db import Store, seed_store

N_EVENTS = len(__import__("json").loads((__import__("pathlib").Path(__file__).resolve().parent.parent / "data" / "events.json").read_text()))

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
    assert len(store.all_events()) == N_EVENTS


def test_post_event_empty_text_422(make):
    c, store = make()
    assert c.post("/api/events", json={"sender": "rami", "text": "   "}).status_code == 422
    assert len(store.all_events()) == N_EVENTS


def test_post_event_jev_down_502_and_stored(make):
    c, store = make(ask=ask_down)
    r = c.post("/api/events", json={"sender": "rami", "text": "hello"})
    assert r.status_code == 502 and r.json()["decision"]["action"] == "error"
    assert len(store.all_events()) == N_EVENTS + 1


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
    assert m["n"] == N_EVENTS and m["settings_changed"] is False
    for col in ("jev", "llm"):
        assert {"critical_misses", "precision", "false_alarm_rate", "cost_per_1k", "p50", "accuracy",
                "accuracy_excl_asks", "asks", "errors"} <= set(m[col])
    assert m["llm"]["errors"] == 0


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
    assert len(store.all_events()) == N_EVENTS and c.get("/api/day").json()["clock"] == "08:00"


def test_moments_in_time_order(make):
    c, _ = make()
    m = c.get("/api/moments").json()
    assert [x["name"] for x in m] == ["loud-vs-quiet", "ci-trio", "unsure", "evening"] and m[0]["time"] == "14:05"


# --- test page support: any source, CI events, custom time, dry runs ---

def ask_ci(state, etype):
    if etype == "ci_failure":
        return {"answers": {"failure_type": {"flaky_test": 0.9, "infra_problem": 0.04, "config_or_lint": 0.03,
                                             "code_regression": 0.03}, "cause_identifiable": 0.9, "blocks_release": 0.1},
                "latency_ms": 5, "usage": {}, "request": {}, "error": None}
    return ask_ok(state, etype)


def test_dry_run_returns_full_response_and_stores_nothing(make):
    c, store = make()
    r = c.post("/api/events", json={"sender": "rami", "text": "checkout broken", "dry_run": True})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["action"] == "interrupt" and body["result"]["state"]["message"] == "checkout broken"
    assert body["dry_run"] is True and len(store.all_events()) == N_EVENTS


def test_custom_time_source_and_channel(make):
    c, _ = make()
    r = c.post("/api/events", json={"sender": "layla", "text": "hi", "source": "email", "channel": "Email",
                                    "time": "19:30", "dry_run": True}).json()
    assert r["event"]["time"] == "19:30" and r["event"]["source"] == "email"
    assert r["result"]["state"]["channel"] == "Email" and "evening" in r["result"]["state"]["now"]
    assert r["decision"]["rule"] == 4  # blocks the release, so evening mode doesn't hold it


def test_bad_time_422(make):
    c, _ = make()
    assert c.post("/api/events", json={"sender": "rami", "text": "x", "time": "7pm"}).status_code == 422


def test_ci_event(make):
    c, _ = make(ask=ask_ci)
    r = c.post("/api/events", json={"type": "ci_failure", "branch": "main", "test_name": "test_cart",
                                    "log_tail": "FAILED test_cart - TimeoutError", "commit_message": "bump deps",
                                    "dry_run": True}).json()
    assert r["event"]["sender"] == "github-actions" and r["result"]["state"]["ci"]["branch"] == "main"
    assert r["decision"]["label"] == "rerun silently"


def test_ci_event_needs_branch_test_and_log(make):
    c, _ = make(ask=ask_ci)
    assert c.post("/api/events", json={"type": "ci_failure", "branch": "main"}).status_code == 422


def test_outsider_sender_by_name(make):
    c, _ = make()
    r = c.post("/api/events", json={"sender_name": "Acme Corp sales", "text": "special offer", "dry_run": True}).json()
    assert r["event"]["sender"] == "unknown:Acme Corp sales" and "Acme Corp sales" in r["result"]["state"]["sender"]


def test_day_has_baseline_decision_for_seeded_events_only(make):
    c, _ = make()
    c.post("/api/clock", json={"time": "14:30"})
    c.post("/api/events", json={"sender": "rami", "text": "checkout is broken"})
    events = {e["id"]: e for e in c.get("/api/day").json()["events"]}
    assert events["evt-015"]["baseline_decision"]["action"] in {"interrupt", "batch", "delegate", "drop", "ask"}
    assert events["evt-034"]["result"]["facts"]["deadline_in_minutes"] == 100
    assert events["live-1"]["baseline_decision"] is None


def test_settings_accept_deadline_minutes(make):
    c, _ = make()
    assert c.put("/api/settings", json={"deadlineMinutes": 60}).json()["deadlineMinutes"] == 60
    assert c.put("/api/settings", json={"deadlineMinutes": 2}).json()["deadlineMinutes"] == 120


def ask_fees(state, etype):
    return {"answers": {**BLOCKER, "blocks_release": 0.05, "time_sensitive": 0.1, "task_later": 0.9},
            "latency_ms": 5, "usage": {}, "request": {}, "error": None}


def test_calendar_lists_connection_and_reminders(make):
    c, _ = make(ask=ask_fees)
    out = c.post("/api/events", json={"sender": "maha", "text": "you need to pay school fees next month"}).json()
    cal = c.get("/api/calendar").json()
    assert cal["connection"]["connected"] is True
    [r] = cal["reminders"]
    assert r["event_id"] == out["event"]["id"] and r["date"] == "2026-12-01"
    assert [e["title"] for e in r["day"]] == ["Quarterly planning", "Standup", "1:1 with Omar"]


def test_reminder_move_to_suggested_and_remove(make):
    c, _ = make(ask=ask_fees)
    eid = c.post("/api/events", json={"sender": "maha", "text": "you need to pay school fees next month"}).json()["event"]["id"]
    r = c.post(f"/api/events/{eid}/reminder", json={"action": "move"}).json()
    assert (r["time"], r["clashes"], r["suggested"]) == ("10:30", [], None)
    assert c.post(f"/api/events/{eid}/reminder", json={"action": "remove"}).json()["status"] == "removed"
    assert c.get("/api/calendar").json()["reminders"] == []
    assert c.post(f"/api/events/{eid}/reminder", json={"action": "fly"}).status_code == 422


# People are configurable from the Rules page (design/14 § People).
def test_add_person_then_message_from_them(make):
    c, _ = make()
    r = c.post("/api/people", json={"name": "Rana Haddad", "role": "Sanad's aunt", "relationship": "family"})
    assert r.status_code == 201
    p = r.json()
    assert p["key"] == "rana-haddad" and p["custom"] is True and p["relationship"] == "family"
    assert any(x["key"] == "rana-haddad" for x in c.get("/api/people").json())
    e = c.post("/api/events", json={"sender": "rana-haddad", "text": "call me when you can"})
    assert e.status_code == 201


def test_add_person_same_name_gets_new_key(make):
    c, _ = make()
    a = c.post("/api/people", json={"name": "Rana", "role": "aunt"}).json()
    b = c.post("/api/people", json={"name": "Rana", "role": "cousin"}).json()
    assert a["key"] == "rana" and b["key"] == "rana-2" and a["relationship"] == "contact"


@pytest.mark.parametrize("body", [{"name": "  ", "role": "x"}, {"name": "A", "role": "x", "relationship": "boss"},
                                  {"name": "x" * 81, "role": "x"}])
def test_add_person_rejects_bad_input(make, body):
    c, _ = make()
    assert c.post("/api/people", json=body).status_code == 422


def test_delete_person_drops_them_from_lists(make):
    c, _ = make()
    key = c.post("/api/people", json={"name": "Rana", "role": "aunt", "relationship": "family"}).json()["key"]
    s = c.get("/api/settings").json()
    c.put("/api/settings", json={**s, "family": s["family"] + [key], "vip": [key]})
    assert c.delete(f"/api/people/{key}").status_code == 200
    s = c.get("/api/settings").json()
    assert key not in s["family"] and key not in s["vip"]
    assert all(x["key"] != key for x in c.get("/api/people").json())


def test_delete_person_only_custom(make):
    c, _ = make()
    assert c.delete("/api/people/maha").status_code == 409
    assert c.delete("/api/people/nobody").status_code == 404
