"""A real Google connection (design/17): OAuth 2.0, Google Calendar and Gmail over plain HTTPS.

Optional. Without GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env, Doorman stays on the demo
calendar and the seeded mail. Tokens live in the local SQLite database (data/doorman.db, gitignored)
and never leave this machine except to Google. Every failed call raises GoogleError; nothing is
silently treated as "no events" or "no mail".
"""
from __future__ import annotations

import os
import secrets
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import httpx

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
SCOPES = ["openid", "email",
          "https://www.googleapis.com/auth/gmail.readonly",      # read mail to route it
          "https://www.googleapis.com/auth/calendar.events"]     # read for clashes, write reminders on request
DEFAULT_REDIRECT = "http://localhost:8000/api/connections/google/callback"
KEY, STATE_KEY = "google", "google_oauth_state"


class GoogleError(RuntimeError):
    pass


class Google:
    def __init__(self, store, env=None, http: httpx.Client | None = None, now=time.time, tz: str | None = None):
        env = os.environ if env is None else env
        self.store, self.now = store, now
        self.client_id, self.client_secret = env.get("GOOGLE_CLIENT_ID"), env.get("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = env.get("GOOGLE_REDIRECT_URI") or DEFAULT_REDIRECT
        self.tz = tz or env.get("DOORMAN_TZ") or "Asia/Amman"
        self.http = http or httpx.Client(timeout=15)

    # ---- connection ----
    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _saved(self) -> dict | None:
        return self.store.get(KEY)

    @property
    def connected(self) -> bool:
        return bool((self._saved() or {}).get("refresh_token"))

    def status(self) -> dict:
        return {"configured": self.configured, "connected": self.connected,
                "account": (self._saved() or {}).get("account") if self.connected else None}

    def auth_url(self) -> str:
        if not self.configured:
            raise GoogleError("Google isn't set up: add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env")
        state = secrets.token_urlsafe(24)
        self.store.put(STATE_KEY, state)
        return AUTH_URL + "?" + urlencode({
            "client_id": self.client_id, "redirect_uri": self.redirect_uri, "response_type": "code",
            "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent",
            "include_granted_scopes": "true", "state": state})

    def finish(self, code: str, state: str) -> str:
        """The OAuth callback: check state, swap the code for tokens, remember the account."""
        expected = self.store.get(STATE_KEY)
        self.store.put(STATE_KEY, None)
        if not expected or not secrets.compare_digest(str(state), expected):
            raise GoogleError("sign-in expired or was tampered with; try connecting again")
        tok = self._token_request({"grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri})
        if not tok.get("refresh_token"):
            raise GoogleError("Google didn't return a refresh token; remove Doorman's access in your Google account and connect again")
        saved = {"access_token": tok["access_token"], "refresh_token": tok["refresh_token"],
                 "expires_at": self.now() + int(tok.get("expires_in", 3600)), "account": None}
        self.store.put(KEY, saved)
        info = self._get(USERINFO_URL)
        self.store.put(KEY, {**saved, "account": info.get("email")})
        return info.get("email")

    def disconnect(self) -> None:
        saved = self._saved() or {}
        if saved.get("refresh_token"):
            try:
                self.http.post(REVOKE_URL, data={"token": saved["refresh_token"]})
            except httpx.HTTPError:
                pass  # forgetting the token locally is what matters
        self.store.put(KEY, None)

    # ---- HTTP ----
    def _token_request(self, form: dict) -> dict:
        r = self.http.post(TOKEN_URL, data={**form, "client_id": self.client_id, "client_secret": self.client_secret})
        if r.status_code != 200:
            raise GoogleError(f"Google token request failed: HTTP {r.status_code}")
        return r.json()

    def _access_token(self) -> str:
        saved = self._saved()
        if not saved or not saved.get("refresh_token"):
            raise GoogleError("Google isn't connected")
        if saved["expires_at"] - 60 <= self.now():
            tok = self._token_request({"grant_type": "refresh_token", "refresh_token": saved["refresh_token"]})
            saved = {**saved, "access_token": tok["access_token"], "expires_at": self.now() + int(tok.get("expires_in", 3600))}
            self.store.put(KEY, saved)
        return saved["access_token"]

    def _call(self, method: str, url: str, **kw) -> dict:
        try:
            r = self.http.request(method, url, headers={"Authorization": f"Bearer {self._access_token()}"}, **kw)
        except httpx.HTTPError as e:
            raise GoogleError(f"couldn't reach Google: {e}") from e
        if r.status_code >= 300:
            raise GoogleError(f"Google returned HTTP {r.status_code} for {url.split('?')[0]}")
        return r.json() if r.content else {}

    def _get(self, url: str, params: dict | None = None) -> dict:
        return self._call("GET", url, params=params)

    # ---- Calendar ----
    def calendar_events(self, day: str) -> list[dict]:
        """Timed events on a date in Doorman's time zone, as {title, start, end} (HH:MM), sorted."""
        zone = ZoneInfo(self.tz)
        start = datetime.fromisoformat(day).replace(tzinfo=zone)
        items = self._get(CALENDAR_URL, {"timeMin": start.isoformat(), "timeMax": (start + timedelta(days=1)).isoformat(),
                                         "singleEvents": "true", "orderBy": "startTime", "maxResults": "100"}).get("items", [])
        out = []
        for it in items:
            if it.get("status") == "cancelled" or "dateTime" not in it.get("start", {}):
                continue  # all-day events don't block a 30-minute reminder
            s = datetime.fromisoformat(it["start"]["dateTime"]).astimezone(zone)
            e = datetime.fromisoformat(it["end"]["dateTime"]).astimezone(zone)
            out.append({"title": it.get("summary") or "(busy)", "start": s.strftime("%H:%M"), "end": e.strftime("%H:%M")})
        return sorted(out, key=lambda x: x["start"])

    def insert_event(self, day: str, start: str, minutes: int, title: str, description: str = "") -> dict:
        begin = datetime.fromisoformat(f"{day}T{start}:00")
        end = begin + timedelta(minutes=minutes)
        ev = self._call("POST", CALENDAR_URL, json={
            "summary": title, "description": description,
            "start": {"dateTime": begin.isoformat(), "timeZone": self.tz},
            "end": {"dateTime": end.isoformat(), "timeZone": self.tz},
            "reminders": {"useDefault": True}})
        return {"id": ev.get("id"), "link": ev.get("htmlLink")}

    # ---- Gmail ----
    def gmail_recent(self, limit: int = 10, query: str = "in:inbox newer_than:1d") -> list[dict]:
        """The newest inbox messages as Gmail API `format=full` resources (what the gmail adapter reads)."""
        ids = [m["id"] for m in self._get(GMAIL_URL, {"q": query, "maxResults": str(limit)}).get("messages", [])]
        return [self._get(f"{GMAIL_URL}/{mid}", {"format": "full"}) for mid in ids]
