"""Sanad's connected calendar (design/16). Demo: Google Calendar API payloads from data/raw/google_calendar.

A real connection would fetch the same `calendar#events` shape with the Calendar API; everything
below reads only that shape. Weekly RRULEs are expanded; nothing else of RFC 5545 is.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

TODAY = "2026-11-14"  # the demo day
RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "google_calendar"
FILES = ("sanad-day.json", "sanad-upcoming.json")
_DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def connection() -> dict:
    return {"connected": True, "provider": "Google Calendar", "account": "sanad@example.com", "demo": True,
            "note": "Demo data in the Google Calendar API format; no account is contacted."}


@lru_cache(maxsize=1)
def _items() -> tuple:
    out = []
    for name in FILES:
        for it in json.loads((RAW / name).read_text())["items"]:
            if it.get("status") == "cancelled" or "dateTime" not in it.get("start", {}):
                continue
            out.append(it)
    return tuple(out)


def _hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def events_on(day: str) -> list[dict]:
    """Timed events on a date (YYYY-MM-DD), sorted by start."""
    d = date.fromisoformat(day)
    out = []
    for it in _items():
        start, end = datetime.fromisoformat(it["start"]["dateTime"]), datetime.fromisoformat(it["end"]["dateTime"])
        rule = next((r for r in it.get("recurrence", []) if r.startswith("RRULE:FREQ=WEEKLY")), None)
        if rule:
            days = rule.split("BYDAY=")[1].split(";")[0].split(",") if "BYDAY=" in rule else [_DAYS[start.weekday()]]
            hit = d >= start.date() and _DAYS[d.weekday()] in days
        else:
            hit = start.date() == d
        if hit:
            out.append({"title": it["summary"], "start": _hhmm(start), "end": _hhmm(end)})
    return sorted(out, key=lambda e: e["start"])


def _plus(hhmm: str, minutes: int) -> str:
    t = datetime.strptime(hhmm, "%H:%M") + timedelta(minutes=minutes)
    return _hhmm(t)


def clashes(day: str, start: str, minutes: int = 30, source=None) -> list[dict]:
    """Events overlapping [start, start+minutes). `source(day)` lists the day's events (demo by default,
    Google Calendar when connected, see server/google.py)."""
    end = _plus(start, minutes)
    return [e for e in (source or events_on)(day) if e["start"] < end and start < e["end"]]


def next_free(day: str, start: str, minutes: int = 30, latest: str = "18:00", source=None) -> str | None:
    """The first start at or after `start` with no clash, stepping to the end of whatever is in the way."""
    t = start
    while t <= latest:
        hit = clashes(day, t, minutes, source)
        if not hit:
            return t
        t = max(e["end"] for e in hit)
    return None
