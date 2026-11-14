"""SQLite store for the app (design/14-app.md § SQLite schema).

Events and model results are JSON columns; decisions are never stored: they are recomputed
from the policy on every read, so a settings change re-routes the whole day.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from pipeline.adapters.base import DEMO_TZ

from .policy import DEFAULTS

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "doorman.db"
DAY_START = "08:00"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, time TEXT, origin TEXT, event TEXT,
                                   label TEXT, holdout INTEGER, demo_moment TEXT);
CREATE TABLE IF NOT EXISTS results (event_id TEXT PRIMARY KEY, result TEXT);
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, kind TEXT,
                                     value TEXT, at TEXT);
"""


class Store:
    def __init__(self, path: Path | str = DB_PATH):
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.executescript(SCHEMA)

    def _q(self, sql, args=()):
        with self.lock:
            cur = self.conn.execute(sql, args)
            self.conn.commit()
            return cur.fetchall()

    def is_empty(self) -> bool:
        return self._q("SELECT COUNT(*) FROM events")[0][0] == 0

    def seed(self, snapshot: dict, events: list[dict], results: dict) -> None:
        with self.lock:
            for table in ("events", "results", "kv", "feedback"):
                self.conn.execute(f"DELETE FROM {table}")
            self.conn.commit()
            for e in events:
                self.add_event(e, results.get(e["id"], {}), origin="seed")
            self.put("snapshot", snapshot)
            self.put("settings", DEFAULTS)
            self.put("clock", DAY_START)

    def add_event(self, event: dict, result: dict, origin: str = "live") -> None:
        event = {**event, "origin": origin}
        with self.lock:
            self.conn.execute("INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?)",
                              (event["id"], event["time"], origin, json.dumps(event, ensure_ascii=False),
                               json.dumps(event.get("label")), int(bool(event.get("holdout"))), event.get("demo_moment")))
            self.conn.execute("INSERT OR REPLACE INTO results VALUES (?,?)",
                              (event["id"], json.dumps(result, ensure_ascii=False)))
            self.conn.commit()

    def all_events(self) -> list[dict]:
        return [json.loads(row[0]) for row in self._q("SELECT event FROM events ORDER BY time, id")]

    def results(self) -> dict:
        return {k: json.loads(v) for k, v in self._q("SELECT event_id, result FROM results")}

    def set_result(self, event_id: str, patch: dict) -> None:
        with self.lock:
            rows = self._q("SELECT result FROM results WHERE event_id = ?", (event_id,))
            current = json.loads(rows[0][0]) if rows else {}
            self._q("INSERT OR REPLACE INTO results VALUES (?,?)",
                    (event_id, json.dumps({**current, **patch}, ensure_ascii=False)))

    def get(self, key: str, default=None):
        rows = self._q("SELECT value FROM kv WHERE key = ?", (key,))
        return json.loads(rows[0][0]) if rows else default

    def put(self, key: str, value) -> None:
        self._q("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, json.dumps(value, ensure_ascii=False)))

    def next_live_id(self) -> str:
        rows = self._q("SELECT id FROM events WHERE origin = 'live'")
        n = max((int(r[0].split("-", 1)[1]) for r in rows), default=0)
        return f"live-{n + 1}"

    def delete_event(self, event_id: str) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
            self.conn.execute("DELETE FROM results WHERE event_id = ?", (event_id,))
            self.conn.commit()

    def add_feedback(self, event_id: str, kind: str, value: str | None) -> dict:
        at = datetime.now(DEMO_TZ).isoformat(timespec="seconds")
        self._q("INSERT INTO feedback (event_id, kind, value, at) VALUES (?,?,?,?)", (event_id, kind, value, at))
        return {"event_id": event_id, "kind": kind, "value": value, "at": at}

    def feedback(self) -> dict:
        out: dict[str, list] = {}
        for event_id, kind, value, at in self._q("SELECT event_id, kind, value, at FROM feedback ORDER BY id"):
            out.setdefault(event_id, []).append({"kind": kind, "value": value, "at": at})
        return out

    def reset_live(self) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM results WHERE event_id IN (SELECT id FROM events WHERE origin = 'live')")
            self.conn.execute("DELETE FROM events WHERE origin = 'live'")
            self.conn.execute("DELETE FROM feedback")
            self.conn.commit()
            self.put("clock", DAY_START)


def seed_store(store: Store) -> None:
    """Load the labelled day and the committed model outputs (pipeline/cache). No network."""
    from pipeline.load import load_events, load_snapshot
    from pipeline.run import build_results

    snapshot = load_snapshot(ROOT / "data" / "snapshot.json")
    events = load_events(ROOT / "data" / "events.json", snapshot)
    results = build_results(snapshot, events, offline=True)
    store.seed(snapshot, events, results["events"])
    store.put("digest", results["digest"])
