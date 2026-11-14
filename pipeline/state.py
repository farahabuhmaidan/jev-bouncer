"""Builds the state Jev sees for one event (design/02-context-builder.md).

Deterministic code, no AI: the same event and snapshot always give the same state.
Budget and user settings are deliberately left out; they belong to the policy.
"""
from __future__ import annotations

import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
EVENING_START = "18:00"
MAX_LOG_LINES = 40

_TICKET = re.compile(r"\b[A-Z]{2,}-\d+\b")
_PR = re.compile(r"#(\d+)\b")


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _current(time: str, calendar: list[dict]) -> dict | None:
    return next((c for c in calendar if c["start"] <= time < c["end"]), None)


def next_free_slot(time: str, snapshot: dict, evening_start: str = EVENING_START) -> str:
    """When Sanad can next look at something: end of the current calendar block,
    else 30 minutes from now; anything reaching the evening waits for 09:00 tomorrow."""
    if time >= evening_start:
        return "09:00 tomorrow"
    calendar = snapshot.get("calendar", [])
    cur = _current(time, calendar)
    slot = cur["end"] if cur else _hhmm(_minutes(time) + 30)
    # Back-to-back blocks: keep walking until a gap.
    while (nxt := _current(slot, calendar)) is not None:
        slot = nxt["end"]
    return "09:00 tomorrow" if slot >= evening_start else slot


def _now(time: str, snapshot: dict) -> str:
    if time >= EVENING_START:
        return f"{time}, after work hours (evening, at home)"
    calendar = snapshot.get("calendar", [])
    cur = _current(time, calendar)
    if cur:
        what = {"focus": "in a focus block", "meeting": f"in a meeting ({cur['title']})",
                "personal": f"away for a personal event ({cur['title']})"}[cur["kind"]]
        return f"{time}, Sanad is {what} until {cur['end']}"
    upcoming = [c for c in calendar if c["start"] > time]
    nxt = f"; next: {upcoming[0]['title']} at {upcoming[0]['start']}" if upcoming else ""
    return f"{time}, Sanad is free{nxt}"


def _sender(key: str, snapshot: dict) -> str:
    if key.startswith("unknown:"):
        return f"Unknown sender ({key.split(':', 1)[1]})"
    p = snapshot["people"][key]
    if p.get("is_bot"):
        return f"{p['name']} (automated)"
    rel = p["relationship"]
    if rel == "team":
        return f"{p['name']}, {p['role']} (Sanad's team: {p['team']})"
    if rel == "family":
        return f"{p['name']} ({p['role']}, family)"
    if rel == "customer":
        return f"{p['name']}, {p['role']} (customer)"
    if rel == "leadership":
        return f"{p['name']}, {p['role']} (company leadership)"
    return f"{p['name']}, {p['role']} ({p['team']} team)"


def _ticket_line(t: dict, people: dict) -> str:
    owner = "Sanad" if t["owner"] == "sanad" else people.get(t["owner"], {}).get("name", t["owner"])
    return f"{t['key']}: {t['title']}, {t['priority']} priority, owned by {owner}, due {t['due']}"


def _linked(text: str, snapshot: dict, branch: str | None = None) -> list[str]:
    lowered = text.lower()
    keys = set(_TICKET.findall(text))
    prs = set(_PR.findall(text))
    out = []
    for t in snapshot.get("tickets", []):
        if t["key"] in keys or any(k.lower() in lowered for k in t.get("keywords", [])):
            out.append(_ticket_line(t, snapshot["people"]))
    for pr in snapshot.get("prs", []):
        if str(pr["number"]) in prs or pr["branch"] == branch or any(k.lower() in lowered for k in pr.get("keywords", [])):
            out.append(f"PR #{pr['number']} on branch {pr['branch']}: {pr['title']}")
    return out


_BY_TIME = re.compile(r"\b(?:by|before)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.I)
_TODAY = re.compile(r"\b(today|end of (the )?day|EOD)\b", re.I)
DAY_END = "18:00"  # "today" and a ticket due today end at 18:00 (design/02)


def _linked_tickets(text: str, snapshot: dict) -> list[dict]:
    lowered, keys = text.lower(), set(_TICKET.findall(text))
    return [t for t in snapshot.get("tickets", [])
            if t["key"] in keys or any(k.lower() in lowered for k in t.get("keywords", []))]


def deadline_minutes(event: dict, snapshot: dict) -> int | None:
    """Minutes from the event until the nearest deadline it states or links to, or None.

    Code, not a Jev field: stored as `facts.deadline_in_minutes` and applied by the policy (row 5).
    Understands "by/before HH:MM" (or "before 11", "by 3pm"), "today", and a linked ticket due today.
    """
    text = event.get("text") or f"{event.get('branch', '')} {event.get('commit_message', '')}"
    now = _minutes(event["time"])
    targets = []
    for h, m, ampm in _BY_TIME.findall(text):
        hour = int(h) % 12 + (12 if ampm.lower() == "pm" else 0) if ampm else int(h)
        if not ampm and hour < 8:  # "before 5" in a workday means 17:00
            hour += 12
        if hour < 24:
            targets.append(hour * 60 + int(m or 0))
    if _TODAY.search(text) or any(t.get("due") == "today" for t in _linked_tickets(text, snapshot)):
        targets.append(_minutes(DAY_END))
    ahead = [t - now for t in targets if t > now]
    return min(ahead) if ahead else None


def _commitment(event: dict, text: str, snapshot: dict) -> str | None:
    """At most one past promise that matches the sender or a linked ticket (design/02, 06)."""
    tickets = {t["key"] for t in _linked_tickets(text, snapshot)}
    for c in snapshot.get("commitments", []):
        about = c.get("about") or []
        on_topic = not about or any(k.lower() in text.lower() for k in about)
        if (c.get("who") == event["sender"] and on_topic) or c.get("ticket") in tickets:
            return f"{c['what']} {c['when']}".strip()
    return None


def _log_tail(event: dict) -> str:
    if event.get("log_tail"):
        return event["log_tail"]
    lines = (DATA / event["log_file"]).read_text().rstrip().splitlines()
    return "\n".join(lines[-MAX_LOG_LINES:])


def _channel(event: dict) -> str:
    if event.get("channel"):
        return event["channel"]
    return {"slack": "Slack DM", "email": "Email"}.get(event["source"], event["source"])


def build_state(event: dict, snapshot: dict) -> dict:
    state = {
        "now": _now(event["time"], snapshot),
        "sanad": f"{snapshot['user']['name']}: {snapshot['user']['role']}",
        "today": snapshot.get("today", ""),
        "sender": _sender(event["sender"], snapshot),
    }
    if event["type"] == "ci_failure":
        state["channel"] = "CI (GitHub Actions)"
        state["ci"] = {
            "branch": event["branch"],
            "test_name": event["test_name"],
            "commit_message": event.get("commit_message", ""),
            "log_tail": _log_tail(event),
        }
        linked = _linked(f"{event['branch']} {event.get('commit_message', '')}", snapshot, event["branch"])
    else:
        state["channel"] = _channel(event)
        state["message"] = event["text"]
        if event.get("bulk_mail"):
            state["mail_type"] = "Bulk or marketing email (has an unsubscribe link)"
        linked = _linked(event["text"], snapshot)
    if linked:
        state["linked_items"] = linked
    commitment = _commitment(event, event.get("text") or event.get("commit_message", ""), snapshot)
    if commitment and event["type"] == "message":
        state["commitment"] = commitment
    return state
