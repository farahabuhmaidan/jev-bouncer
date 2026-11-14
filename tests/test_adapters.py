"""Contract tests for every registered adapter (design/13-adapters.md).

New adapters are picked up automatically: add a module + fixtures, no test edits.
"""
import base64
import json
import re
import socket
from pathlib import Path

import pytest

from pipeline.adapters import ADAPTERS, CONTEXT_ADAPTERS, resolve_sender

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PEOPLE = json.loads((ROOT / "data" / "snapshot.json").read_text())["people"]
REQUIRED = {"id": str, "time": str, "type": str, "source": str, "sender": str}


def _fixtures(source):
    return sorted((RAW / source).glob("*.json"))


EVENT_CASES = [(name, f) for name in ADAPTERS for f in _fixtures(name)]
CONTEXT_CASES = [(name, f) for name in CONTEXT_ADAPTERS for f in _fixtures(name)]


@pytest.fixture
def no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("adapters must not touch the network")
    monkeypatch.setattr(socket, "socket", boom)


def test_every_adapter_has_a_fixture():
    for name in list(ADAPTERS) + list(CONTEXT_ADAPTERS):
        assert _fixtures(name), f"no fixture in data/raw/{name}/"


@pytest.mark.parametrize("name,path", EVENT_CASES, ids=lambda x: getattr(x, "name", x))
def test_event_adapter_contract(name, path, no_network):
    event = ADAPTERS[name].to_event(json.loads(path.read_text()), PEOPLE)
    for key, typ in REQUIRED.items():
        assert isinstance(event.get(key), typ), (key, event)
    assert re.fullmatch(r"\d\d:\d\d", event["time"])
    assert event["type"] in {"message", "ci_failure"}
    assert event["sender"] in PEOPLE or event["sender"].startswith("unknown:")
    if event["type"] == "message":
        assert isinstance(event.get("text"), str) and event["text"]
    else:
        assert event.get("branch") and event.get("test_name") and event.get("log_tail")


@pytest.mark.parametrize("name,path", CONTEXT_CASES, ids=lambda x: getattr(x, "name", x))
def test_context_adapter_contract(name, path, no_network):
    items = CONTEXT_ADAPTERS[name].to_context(json.loads(path.read_text()))
    assert items
    for it in items:
        assert re.fullmatch(r"\d\d:\d\d", it["start"]) and re.fullmatch(r"\d\d:\d\d", it["end"])
        assert it["start"] < it["end"]
        assert it["kind"] in {"meeting", "focus", "personal"}


def test_resolve_sender_known_and_unknown():
    assert resolve_sender("slack", "U07RAMI", PEOPLE) == "rami"
    assert resolve_sender("email", "Layla <layla@example.com>", PEOPLE) == "layla"
    assert resolve_sender("slack", "U0NOBODY", PEOPLE) == "unknown:U0NOBODY"


def _slack(text, **event):
    return {"type": "event_callback", "event": {"type": "message", "user": "U07LAYLA", "text": text,
                                                "ts": "1794657900.000100", "channel": "D01", "channel_type": "im", **event}}


def test_slack_mention_resolved():
    ev = ADAPTERS["slack"].to_event(_slack("<@U07RAMI> can you check this?"), PEOPLE)
    assert ev["text"] == "Rami can you check this?"


def test_slack_dm_channel():
    assert ADAPTERS["slack"].to_event(_slack("hi"), PEOPLE)["channel"] == "Slack DM"


def test_slack_bot_message_is_bot_sender():
    ev = ADAPTERS["slack"].to_event(_slack("deploy done", bot_id="B01", user=None, subtype="bot_message"), PEOPLE)
    assert ev["sender"].startswith("unknown:") or PEOPLE[ev["sender"]]["is_bot"]
    assert ev["is_bot"] is True


def _gmail(body, headers=()):
    data = base64.urlsafe_b64encode(body.encode()).decode().rstrip("=")
    return {"id": "m1", "threadId": "t1", "internalDate": "1794672600000",
            "payload": {"mimeType": "multipart/alternative",
                        "headers": [{"name": "From", "value": "Riverside School <office@riverside-school.example.org>"},
                                    {"name": "Subject", "value": "Hello"}, *headers],
                        "parts": [{"mimeType": "text/plain", "body": {"data": data}}]}}


def test_gmail_base64_body_decoded():
    ev = ADAPTERS["gmail"].to_event(_gmail("Please call us back."), PEOPLE)
    assert "Please call us back." in ev["text"] and ev["sender"] == "school"


def test_gmail_quoted_history_cut():
    ev = ADAPTERS["gmail"].to_event(_gmail("New reply here.\n\nOn Mon, Nov 9, Sanad wrote:\n> old stuff"), PEOPLE)
    assert "old stuff" not in ev["text"] and "New reply here." in ev["text"]


def test_gmail_unsubscribe_hint():
    ev = ADAPTERS["gmail"].to_event(_gmail("Deals!", [{"name": "List-Unsubscribe", "value": "<mailto:u@x>"}]), PEOPLE)
    assert ev["bulk_mail"] is True


def _cal(*items):
    return {"items": list(items)}


def _item(summary, start, end, **kw):
    return {"summary": summary, "status": "confirmed", "start": {"dateTime": f"2026-11-14T{start}:00+03:00"},
            "end": {"dateTime": f"2026-11-14T{end}:00+03:00"}, **kw}


def test_calendar_focus_time_kind():
    out = CONTEXT_ADAPTERS["google_calendar"].to_context(_cal(_item("Deep work", "14:00", "16:00", eventType="focusTime")))
    assert out == [{"start": "14:00", "end": "16:00", "title": "Deep work", "kind": "focus"}]


def test_calendar_pickup_is_personal():
    out = CONTEXT_ADAPTERS["google_calendar"].to_context(_cal(_item("School pickup", "17:30", "18:00")))
    assert out[0]["kind"] == "personal"


def test_calendar_skips_cancelled_and_free():
    out = CONTEXT_ADAPTERS["google_calendar"].to_context(_cal(
        _item("Old sync", "10:00", "10:30", status="cancelled"),
        _item("Optional talk", "13:00", "14:00", transparency="transparent"),
        _item("Standup", "09:30", "09:45")))
    assert [o["title"] for o in out] == ["Standup"]


def test_github_short_log_kept_whole_with_diff():
    raw = json.loads((RAW / "github_actions" / "regression.json").read_text())
    ev = ADAPTERS["github_actions"].to_event(raw, PEOPLE)
    assert "plan.discount * plan.price" in ev["log_tail"] and "AssertionError" in ev["log_tail"]
