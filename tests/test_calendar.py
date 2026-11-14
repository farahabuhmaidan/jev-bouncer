"""The connected calendar (demo data in Google Calendar format) and clash checks."""
from server.calendar import clashes, connection, events_on, next_free


def test_connection_is_demo_google_calendar():
    c = connection()
    assert c["connected"] is True and c["provider"] == "Google Calendar" and c["demo"] is True


def test_events_on_today_and_later():
    assert any(e["title"] == "Standup" for e in events_on("2026-11-14"))
    assert any(e["title"] == "Quarterly planning" for e in events_on("2026-12-01"))


def test_clash_and_next_free_slot():
    c = clashes("2026-12-01", "09:00", 30)
    assert [e["title"] for e in c] == ["Quarterly planning"]
    assert next_free("2026-12-01", "09:00", 30) == "10:30"
    assert clashes("2026-12-01", "15:00", 30) == []
