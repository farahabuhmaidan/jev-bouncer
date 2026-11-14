"""When is a task in a message due? Code, not a model: phrases map to a date and a time.

Used for reminders (design/16). Only dates after today count; same-day times are the deadline
fact's job (state.deadline_minutes).
"""
from __future__ import annotations

import re
from datetime import date, timedelta

DEFAULT_TIME = "09:00"  # a reminder with no time lands at the start of the working day
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
          "october", "november", "december"]
_MON = "|".join(m[:3] + r"[a-z]*" for m in MONTHS)
_TIME = r"(?:\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?"

_RULES = [
    ("tomorrow", re.compile(r"\btomorrow" + _TIME, re.I)),
    ("next_month", re.compile(r"\bnext month" + _TIME, re.I)),
    ("next_week", re.compile(r"\bnext week" + _TIME, re.I)),
    ("in_n", re.compile(r"\bin (\d+) (day|week)s?" + _TIME, re.I)),
    ("weekday", re.compile(r"\b(?:on |this |next )?(" + "|".join(WEEKDAYS) + ")" + _TIME, re.I)),
    ("day_month", re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)? (?:of )?(" + _MON + r")\b" + _TIME, re.I)),
    ("month_day", re.compile(r"\b(" + _MON + r") (\d{1,2})(?:st|nd|rd|th)?\b" + _TIME, re.I)),
]


def _clock(h, m, ampm) -> str:
    if not h:
        return DEFAULT_TIME
    hour = int(h) % 12 + (12 if ampm.lower() == "pm" else 0) if ampm else int(h)
    if not ampm and hour < 8:  # "at 4" on a working day means 16:00
        hour += 12
    return f"{hour:02d}:{int(m or 0):02d}"


def _month(name: str) -> int:
    return next(i + 1 for i, m in enumerate(MONTHS) if m.startswith(name[:3].lower()))


def _on_or_after(d: date, today: date) -> date:
    return d if d > today else d.replace(year=d.year + 1)


def resolve_when(text: str, today: date, now: str) -> dict | None:
    """The first future date the text names, as {date, time, phrase}, or None."""
    for kind, rx in _RULES:
        m = rx.search(text or "")
        if not m:
            continue
        g = m.groups()
        if kind == "tomorrow":
            d, t = today + timedelta(days=1), g[0:3]
        elif kind == "next_month":
            d = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
            t = g[0:3]
        elif kind == "next_week":
            d, t = today + timedelta(days=7 - today.weekday()), g[0:3]
        elif kind == "in_n":
            d = today + timedelta(days=int(g[0]) * (7 if g[1].lower() == "week" else 1))
            t = g[2:5]
        elif kind == "weekday":
            ahead = (WEEKDAYS.index(g[0].lower()) - today.weekday()) % 7 or 7
            d, t = today + timedelta(days=ahead), g[1:4]
        elif kind == "day_month":
            d, t = _on_or_after(date(today.year, _month(g[1]), int(g[0])), today), g[2:5]
        else:
            d, t = _on_or_after(date(today.year, _month(g[0]), int(g[1])), today), g[2:5]
        return {"date": d.isoformat(), "time": _clock(*t), "phrase": m.group(0).strip()}
    return None
