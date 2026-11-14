"""Load the demo day through the source adapters (design/13-adapters.md).

An entry in events.json is either already a unified event, or raw:
    {"id": ..., "raw_source": "slack", "raw": {...} | "raw_file": "raw/slack/x.json", "label": ...}
A snapshot section may likewise be {"raw_source": "google_calendar", "raw_file": ...}.
"""
from __future__ import annotations

import json
from pathlib import Path

from .adapters import ADAPTERS, CONTEXT_ADAPTERS

CARRIED = ("id", "label", "holdout", "demo_moment")


def _raw(entry: dict, base: Path) -> dict:
    if "raw_file" in entry:
        return json.loads((base / entry["raw_file"]).read_text())
    return entry["raw"]


def load_snapshot(path) -> dict:
    path = Path(path)
    snap = json.loads(path.read_text())
    for section, value in list(snap.items()):
        if isinstance(value, dict) and "raw_source" in value:
            name = value["raw_source"]
            if name not in CONTEXT_ADAPTERS:
                raise ValueError(f"unknown context source {name!r} in snapshot section {section!r}")
            kw = {}
            if name == "google_calendar" and snap.get("user", {}).get("personal_keywords"):
                kw["personal_keywords"] = tuple(snap["user"]["personal_keywords"])
            snap[section] = CONTEXT_ADAPTERS[name].to_context(_raw(value, path.parent), **kw)
    return snap


def load_events(path, snapshot: dict) -> list[dict]:
    path = Path(path)
    out = []
    for entry in json.loads(path.read_text()):
        if "raw_source" in entry:
            name = entry["raw_source"]
            if name not in ADAPTERS:
                raise ValueError(f"unknown event source {name!r} (entry {entry.get('id')})")
            event = ADAPTERS[name].to_event(_raw(entry, path.parent), snapshot["people"])
            event.update({k: entry[k] for k in CARRIED if k in entry})
        else:
            event = dict(entry)
        out.append(event)
    return sorted(out, key=lambda e: (e["time"], e["id"]))
