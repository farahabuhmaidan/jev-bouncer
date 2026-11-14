"""FastAPI backend (design/14-app.md § API). Run: `make app` (uvicorn server.app:main_app --factory)."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline.adapters import ADAPTERS
from pipeline.jev import ask_jev

from . import calendar
from .db import DB_PATH, Store, seed_store
from .live import baseline_decisions, decisions, place_reminder, process_event
from .metrics import compute_metrics
from .policy import effective_settings

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "frontend" / "dist"
HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")
ACTIONS = {"interrupt", "batch", "delegate", "drop"}


class NewEvent(BaseModel):
    """A message (sender + text) or a CI failure (branch, test_name, log_tail). Used by Compose and /test."""
    type: str = "message"
    source: str | None = None
    sender: str | None = None
    sender_name: str | None = None  # someone not in the snapshot, e.g. an outside company
    text: str | None = None
    channel: str | None = None
    time: str | None = None
    branch: str | None = None
    test_name: str | None = None
    commit_message: str | None = None
    log_tail: str | None = None
    dry_run: bool = False


class Clock(BaseModel):
    time: str


class ReminderAction(BaseModel):
    action: str


class Feedback(BaseModel):
    kind: str
    choice: str | None = None


def _safe(ask):
    """A model call that cannot raise: a missing key or a network failure becomes an error result."""
    def call(state, event_type):
        try:
            return ask(state, event_type)
        except KeyError as exc:
            return {"answers": {}, "latency_ms": None, "usage": {}, "request": {},
                    "error": f"missing {exc.args[0]}: add it to .env to route live events"}
        except Exception as exc:  # noqa: BLE001
            return {"answers": {}, "latency_ms": None, "usage": {}, "request": {}, "error": f"{type(exc).__name__}: {exc}"}
    return call


def create_app(store: Store, ask=ask_jev, write=True) -> FastAPI:
    app = FastAPI(title="Doorman")
    ask = _safe(ask)

    def snapshot():
        return store.get("snapshot")

    def respond(out):
        status = 502 if out["decision"]["action"] == "error" else 201
        return JSONResponse(out, status_code=status)

    @app.get("/api/day")
    def day():
        clock, settings = store.get("clock"), effective_settings(store.get("settings"))
        results, routed, fb = store.results(), decisions(store), store.feedback()
        base = baseline_decisions(store)
        visible = [e for e in store.all_events() if e["time"] <= clock]
        visible.sort(key=lambda e: (e["time"], e["id"]), reverse=True)
        urgent = {k for k, items in fb.items() if any(i["kind"] == "urgent" for i in items)}
        used = sum(1 for e in visible if routed[e["id"]]["uses_budget"])
        return {
            "clock": clock, "settings": settings, "evening": clock >= settings["eveningStart"],
            "budget": {"total": settings["budget"], "left": settings["budget"] - used},
            "events": [{**e, "result": results.get(e["id"]), "decision": routed[e["id"]],
                        "baseline_decision": base.get(e["id"]), "feedback": fb.get(e["id"], [])} for e in visible],
            "phone": [e["id"] for e in visible if routed[e["id"]]["action"] == "interrupt" or e["id"] in urgent],
        }

    @app.get("/api/events/{event_id}")
    def event_detail(event_id: str):
        event = next((e for e in store.all_events() if e["id"] == event_id), None)
        if not event:
            raise HTTPException(404, "no such event")
        return {**event, "result": store.results().get(event_id), "decision": decisions(store)[event_id],
                "baseline_decision": baseline_decisions(store).get(event_id), "feedback": store.feedback().get(event_id, [])}

    @app.post("/api/events")
    def new_event(body: NewEvent):
        if body.time is not None and not HHMM.fullmatch(body.time):
            raise HTTPException(422, "time must be HH:MM")
        if body.type == "ci_failure":
            if not (body.branch and body.test_name and body.log_tail):
                raise HTTPException(422, "a CI failure needs branch, test_name and log_tail")
            event = {"type": "ci_failure", "source": body.source or "github_actions", "sender": "github-actions",
                     "branch": body.branch, "test_name": body.test_name,
                     "commit_message": body.commit_message or "", "log_tail": body.log_tail}
        elif body.type == "message":
            if body.sender_name and body.sender_name.strip():
                sender = f"unknown:{body.sender_name.strip()}"
            elif body.sender in snapshot()["people"] and body.sender != "sanad":
                sender = body.sender
            else:
                raise HTTPException(422, f"unknown sender {body.sender!r}; pick a person or give sender_name")
            text = (body.text or "").strip()
            if not text or len(text) > 2000:
                raise HTTPException(422, "text must be 1-2000 characters")
            event = {"type": "message", "source": body.source or "compose", "sender": sender, "text": text,
                     "channel": body.channel or ("Email" if body.source in ("email", "gmail") else "Slack DM")}
        else:
            raise HTTPException(422, "type must be 'message' or 'ci_failure'")
        out = process_event(store, event, ask=ask, write=write, at=body.time, dry_run=body.dry_run)
        if body.dry_run:
            return JSONResponse(out, status_code=200)
        return respond(out)

    @app.post("/api/ingest/{source}")
    async def ingest(source: str, request: Request):
        adapter = ADAPTERS.get(source)
        if not adapter:
            raise HTTPException(404, f"no adapter for {source!r}; have {sorted(ADAPTERS)}")
        try:
            event = adapter.to_event(await request.json(), snapshot()["people"])
        except Exception as exc:  # noqa: BLE001 - a payload the adapter can't read
            raise HTTPException(422, f"{source} adapter could not read the payload: {type(exc).__name__}: {exc}")
        return respond(process_event(store, event, ask=ask, write=write))

    @app.get("/api/settings")
    def get_settings():
        return effective_settings(store.get("settings"))

    @app.put("/api/settings")
    def put_settings(body: dict):
        s = effective_settings({**store.get("settings"), **body})
        store.put("settings", s)
        return s

    @app.post("/api/clock")
    def set_clock(body: Clock):
        if not HHMM.fullmatch(body.time):
            raise HTTPException(422, "time must be HH:MM")
        store.put("clock", body.time)
        return {"clock": body.time}

    @app.post("/api/events/{event_id}/feedback", status_code=201)
    def feedback(event_id: str, body: Feedback):
        if event_id not in store.results():
            raise HTTPException(404, "no such event")
        if body.kind == "ask" and body.choice in ACTIONS:
            return store.add_feedback(event_id, "ask", body.choice)
        if body.kind == "urgent":
            return store.add_feedback(event_id, "urgent", None)
        raise HTTPException(422, "kind must be 'urgent', or 'ask' with a choice of interrupt/batch/delegate/drop")

    @app.get("/api/calendar")
    def get_calendar():
        """The connected calendar and the reminders Doorman added, each with that day's events."""
        events = {e["id"]: e for e in store.all_events()}
        reminders = [{"event_id": eid, "sender": (r.get("state") or {}).get("sender"), "message": events[eid].get("text"),
                      **r["reminder"], "day": calendar.events_on(r["reminder"]["date"])}
                     for eid, r in store.results().items()
                     if eid in events and (r.get("reminder") or {}).get("status") == "added"]
        return {"connection": calendar.connection(), "today": calendar.TODAY,
                "reminders": sorted(reminders, key=lambda x: (x["date"], x["time"]))}

    @app.post("/api/events/{event_id}/reminder")
    def reminder_action(event_id: str, body: ReminderAction):
        rem = (store.results().get(event_id) or {}).get("reminder")
        if not rem or rem.get("status") == "error":
            raise HTTPException(404, "this message has no reminder")
        if body.action == "move" and rem.get("suggested"):
            rem = place_reminder({**rem, "time": rem["suggested"]}, rem["title"], rem["p"])
        elif body.action == "remove":
            rem = {**rem, "status": "removed"}
        elif body.action == "add":
            rem = place_reminder(rem, rem["title"], rem["p"])
        elif body.action != "keep":
            raise HTTPException(422, "action must be move, keep, remove or add")
        store.set_result(event_id, {"reminder": rem})
        return rem

    @app.get("/api/metrics")
    def metrics():
        return compute_metrics(store.all_events(), decisions(store), store.results(), store.get("settings"),
                               baseline=decisions(store, "baseline"))

    @app.get("/api/digest")
    def digest():
        routed = decisions(store)
        groups = [{**g, "items": [i for i in g["items"] if (routed.get(i["event_id"]) or {}).get("action") == "batch"]}
                  for g in (store.get("digest") or {}).get("groups", [])]
        return {"groups": [g for g in groups if g["items"]]}

    @app.get("/api/moments")
    def moments():
        out = []
        for e in store.all_events():
            if e.get("demo_moment") and all(m["name"] != e["demo_moment"] for m in out):
                out.append({"name": e["demo_moment"], "time": e["time"]})
        return out

    @app.get("/api/people")
    def people():
        return [{"key": k, **p} for k, p in snapshot()["people"].items() if k != "sanad"]

    @app.post("/api/reset")
    def reset():
        store.reset_live()
        return {"clock": store.get("clock")}

    if (ROOT / "slides").exists():
        app.mount("/slides", StaticFiles(directory=ROOT / "slides", html=True), name="slides")
    if DIST.exists():
        app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

        @app.get("/{path:path}")
        def spa(path: str):
            f = DIST / path
            return FileResponse(f if path and f.is_file() else DIST / "index.html")
    return app


def main_app() -> FastAPI:
    """The app `make app` serves (uvicorn --factory): real models, data/doorman.db, seeded on first start."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    store = Store(DB_PATH)
    if store.is_empty():
        seed_store(store)
    return create_app(store)

