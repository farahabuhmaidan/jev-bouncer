"""Adapter contract and registry (design/13-adapters.md).

Event adapters turn one raw payload from a source into a unified event.
Context adapters turn a raw payload into one section of the snapshot.
Both are pure: no network, no clock. `fetch()` is the optional live pull.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Protocol
from zoneinfo import ZoneInfo

# The demo persona's timezone. Every source timestamp is shown in this zone.
DEMO_TZ = ZoneInfo("Asia/Amman")

ADAPTERS: dict[str, "Adapter"] = {}
CONTEXT_ADAPTERS: dict[str, "ContextAdapter"] = {}


class Adapter(Protocol):
    source: str
    event_type: str

    def to_event(self, raw: dict, people: dict) -> dict: ...

    def fetch(self, **kwargs) -> list[dict]: ...


class ContextAdapter(Protocol):
    source: str
    section: str

    def to_context(self, raw: dict) -> list[dict]: ...

    def fetch(self, **kwargs) -> dict: ...


def register(cls):
    """Class decorator: registers an instance under `cls.source` in the right registry."""
    inst = cls()
    target = CONTEXT_ADAPTERS if hasattr(inst, "to_context") else ADAPTERS
    if inst.source in target:
        raise ValueError(f"adapter {inst.source!r} registered twice")
    target[inst.source] = inst
    return cls


_EMAIL = re.compile(r"<([^>]+)>")


def resolve_sender(source: str, handle: str | None, people: dict) -> str:
    """Map a source handle (Slack id, email address, GitHub login) to a person key.

    `source` is the handle kind: "slack", "email" or "github". Unknown handles
    come back as "unknown:<handle>" so the state can still say who it was.
    """
    if not handle:
        return "unknown:?"
    m = _EMAIL.search(handle)
    raw = (m.group(1) if m else handle).strip()
    for key, person in people.items():
        value = (person.get("handles") or {}).get(source)
        if value and value.lower() == raw.lower():
            return key
    return f"unknown:{raw}"


def local_hhmm(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(DEMO_TZ).strftime("%H:%M")
