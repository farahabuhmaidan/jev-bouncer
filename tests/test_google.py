"""Real Google connection (design/17): OAuth, Calendar and Gmail, with Google's HTTP faked."""
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from server.db import Store
from server.google import Google, GoogleError

ENV = {"GOOGLE_CLIENT_ID": "cid", "GOOGLE_CLIENT_SECRET": "secret"}


class FakeGoogleHTTP:
    """Answers the handful of Google endpoints Doorman calls, and records every request."""

    def __init__(self):
        self.calls = []
        self.token_n = 0
        self.inserted = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls.append(req)
        url = str(req.url)
        if url.startswith("https://oauth2.googleapis.com/token"):
            form = parse_qs(req.content.decode())
            self.token_n += 1
            if form["grant_type"] == ["authorization_code"]:
                assert form["code"] == ["the-code"] and form["client_secret"] == ["secret"]
                return httpx.Response(200, json={"access_token": "at1", "refresh_token": "rt", "expires_in": 3600,
                                                 "scope": "openid email"})
            assert form["refresh_token"] == ["rt"]
            return httpx.Response(200, json={"access_token": f"at{self.token_n}", "expires_in": 3600})
        if url.startswith("https://openidconnect.googleapis.com/v1/userinfo"):
            return httpx.Response(200, json={"email": "me@example.com"})
        if url.startswith("https://oauth2.googleapis.com/revoke"):
            return httpx.Response(200)
        if url.startswith("https://www.googleapis.com/calendar/v3/calendars/primary/events"):
            if req.method == "POST":
                body = json.loads(req.content)
                self.inserted.append(body)
                return httpx.Response(200, json={"id": "g1", "htmlLink": "https://calendar.google.com/event?eid=g1"})
            return httpx.Response(200, json={"items": [
                {"summary": "Dentist", "start": {"dateTime": "2026-12-01T09:00:00+02:00"}, "end": {"dateTime": "2026-12-01T10:00:00+02:00"}},
                {"summary": "All day", "start": {"date": "2026-12-01"}, "end": {"date": "2026-12-02"}},
                {"summary": "Gone", "status": "cancelled", "start": {"dateTime": "2026-12-01T12:00:00+02:00"}, "end": {"dateTime": "2026-12-01T13:00:00+02:00"}},
            ]})
        if url.startswith("https://gmail.googleapis.com/gmail/v1/users/me/messages/"):
            mid = url.rsplit("/", 1)[1].split("?")[0]
            return httpx.Response(200, json={"id": mid, "threadId": "t", "internalDate": "1794650000000",
                                             "payload": {"mimeType": "text/plain", "headers": [{"name": "From", "value": "A <a@b.c>"}],
                                                         "body": {"data": "aGk"}}})
        if url.startswith("https://gmail.googleapis.com/gmail/v1/users/me/messages"):
            return httpx.Response(200, json={"messages": [{"id": "m1"}, {"id": "m2"}]})
        return httpx.Response(404)


@pytest.fixture
def g(tmp_path):
    fake = FakeGoogleHTTP()
    clock = {"t": 1000.0}
    google = Google(Store(tmp_path / "g.db"), env=ENV, http=httpx.Client(transport=httpx.MockTransport(fake)),
                    now=lambda: clock["t"], tz="Asia/Amman")
    return google, fake, clock


def connect(google):
    state = parse_qs(urlparse(google.auth_url()).query)["state"][0]
    return google.finish("the-code", state)


def test_not_configured_without_client_id(tmp_path):
    google = Google(Store(tmp_path / "x.db"), env={})
    s = google.status()
    assert s == {"configured": False, "connected": False, "account": None}
    with pytest.raises(GoogleError):
        google.auth_url()


def test_auth_url_asks_for_offline_gmail_and_calendar(g):
    google, _, _ = g
    q = parse_qs(urlparse(google.auth_url()).query)
    assert q["client_id"] == ["cid"] and q["access_type"] == ["offline"] and q["response_type"] == ["code"]
    assert "https://www.googleapis.com/auth/gmail.readonly" in q["scope"][0]
    assert "https://www.googleapis.com/auth/calendar.events" in q["scope"][0]
    assert q["redirect_uri"] == ["http://localhost:8000/api/connections/google/callback"]


def test_finish_rejects_wrong_state(g):
    google, _, _ = g
    google.auth_url()
    with pytest.raises(GoogleError):
        google.finish("the-code", "forged")
    assert google.status()["connected"] is False


def test_finish_connects_and_stores_account(g):
    google, _, _ = g
    assert connect(google) == "me@example.com"
    assert google.status() == {"configured": True, "connected": True, "account": "me@example.com"}


def test_token_refreshes_when_expired(g):
    google, fake, clock = g
    connect(google)
    google.calendar_events("2026-12-01")
    clock["t"] += 4000  # past expires_in
    google.calendar_events("2026-12-01")
    auths = [c.headers.get("authorization") for c in fake.calls if "calendar" in str(c.url)]
    assert auths == ["Bearer at1", "Bearer at2"]


def test_calendar_events_in_local_time_skipping_all_day_and_cancelled(g):
    google, fake, _ = g
    connect(google)
    assert google.calendar_events("2026-12-01") == [{"title": "Dentist", "start": "10:00", "end": "11:00"}]
    q = parse_qs(urlparse(str(fake.calls[-1].url)).query)
    assert q["singleEvents"] == ["true"] and q["timeMin"][0].startswith("2026-12-01T00:00:00")


def test_insert_reminder_event(g):
    google, fake, _ = g
    connect(google)
    out = google.insert_event("2026-12-01", "10:30", 30, "Pay school fees", "From Maha")
    assert out == {"id": "g1", "link": "https://calendar.google.com/event?eid=g1"}
    body = fake.inserted[0]
    assert body["summary"] == "Pay school fees" and body["start"]["dateTime"] == "2026-12-01T10:30:00"
    assert body["end"]["dateTime"] == "2026-12-01T11:00:00" and body["start"]["timeZone"] == "Asia/Amman"


def test_gmail_recent_returns_full_messages(g):
    google, _, _ = g
    connect(google)
    msgs = google.gmail_recent(limit=5)
    assert [m["id"] for m in msgs] == ["m1", "m2"] and "payload" in msgs[0]


def test_calls_fail_loudly_when_not_connected(g):
    google, _, _ = g
    with pytest.raises(GoogleError):
        google.calendar_events("2026-12-01")


def test_disconnect_forgets_tokens(g):
    google, fake, _ = g
    connect(google)
    google.disconnect()
    assert google.status()["connected"] is False
    assert any("revoke" in str(c.url) for c in fake.calls)
