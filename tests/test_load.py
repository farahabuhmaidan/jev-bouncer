import json

import pytest

from pipeline.load import load_events, load_snapshot

SNAP = {"user": {"name": "Sanad"}, "people": {"rami": {"name": "Rami", "handles": {"slack": "U07RAMI"}, "is_bot": False}}}
SLACK = {"type": "event_callback", "event": {"type": "message", "user": "U07RAMI", "text": "hi",
                                             "ts": "1794658800.000000", "channel": "D1", "channel_type": "im"}}


def _write(tmp_path, name, obj):
    p = tmp_path / name
    p.write_text(json.dumps(obj))
    return p


def test_load_events_merges_label_from_raw_entry(tmp_path):
    p = _write(tmp_path, "events.json", [{"id": "evt-015", "raw_source": "slack", "raw": SLACK,
                                          "label": {"action": "interrupt"}, "holdout": False, "demo_moment": "loud-vs-quiet"}])
    [e] = load_events(p, SNAP)
    assert e["id"] == "evt-015" and e["sender"] == "rami" and e["text"] == "hi"
    assert e["label"] == {"action": "interrupt"} and e["demo_moment"] == "loud-vs-quiet"


def test_load_events_reads_raw_file_relative_to_events(tmp_path):
    _write(tmp_path, "rami.json", SLACK)
    p = _write(tmp_path, "events.json", [{"id": "e1", "raw_source": "slack", "raw_file": "rami.json", "label": {"action": "batch"}}])
    assert load_events(p, SNAP)[0]["sender"] == "rami"


def test_unified_entries_pass_through_sorted_by_time_then_id(tmp_path):
    p = _write(tmp_path, "events.json", [
        {"id": "b", "time": "10:00", "type": "message", "source": "slack", "sender": "rami", "text": "x", "label": {"action": "drop"}},
        {"id": "a", "time": "10:00", "type": "message", "source": "slack", "sender": "rami", "text": "y", "label": {"action": "drop"}},
        {"id": "c", "time": "09:00", "type": "message", "source": "slack", "sender": "rami", "text": "z", "label": {"action": "drop"}}])
    assert [e["id"] for e in load_events(p, SNAP)] == ["c", "a", "b"]


def test_unknown_raw_source_raises(tmp_path):
    p = _write(tmp_path, "events.json", [{"id": "e1", "raw_source": "teams", "raw": {}, "label": {"action": "drop"}}])
    with pytest.raises(ValueError, match="teams"):
        load_events(p, SNAP)


def test_load_snapshot_expands_raw_calendar(tmp_path):
    cal = {"items": [{"summary": "Focus", "status": "confirmed", "eventType": "focusTime",
                      "start": {"dateTime": "2026-11-14T14:00:00+03:00"}, "end": {"dateTime": "2026-11-14T16:00:00+03:00"}}]}
    _write(tmp_path, "cal.json", cal)
    p = _write(tmp_path, "snapshot.json", {**SNAP, "calendar": {"raw_source": "google_calendar", "raw_file": "cal.json"}})
    assert load_snapshot(p)["calendar"] == [{"start": "14:00", "end": "16:00", "title": "Focus", "kind": "focus"}]
