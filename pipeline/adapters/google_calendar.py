"""Google Calendar `events.list` responses → the snapshot's `calendar` section.

A real connection needs Google OAuth with the calendar.readonly scope; see design/13.
"""
from __future__ import annotations

from datetime import datetime

from .base import local_hhmm, register

PERSONAL_KEYWORDS = ("pickup", "school", "dentist", "doctor", "family")


@register
class GoogleCalendarAdapter:
    source = "google_calendar"
    section = "calendar"

    def to_context(self, raw: dict, personal_keywords=PERSONAL_KEYWORDS) -> list[dict]:
        out = []
        for item in raw.get("items", []):
            if item.get("status") == "cancelled" or item.get("transparency") == "transparent":
                continue
            start, end = item.get("start", {}), item.get("end", {})
            if "dateTime" not in start:  # all-day events are skipped for the demo
                continue
            title = item.get("summary", "(no title)")
            if item.get("eventType") == "focusTime":
                kind = "focus"
            elif item.get("eventType") == "outOfOffice" or any(k in title.lower() for k in personal_keywords):
                kind = "personal"
            else:
                kind = "meeting"
            out.append({
                "start": local_hhmm(datetime.fromisoformat(start["dateTime"])),
                "end": local_hhmm(datetime.fromisoformat(end["dateTime"])),
                "title": title,
                "kind": kind,
            })
        return sorted(out, key=lambda c: c["start"])

    def fetch(self, **kwargs) -> dict:
        raise NotImplementedError("needs Google OAuth (calendar.readonly); see design/13-adapters.md")
