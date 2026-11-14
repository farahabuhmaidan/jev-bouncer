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

from .db import DB_PATH, Store, seed_store
from .live import decisions, process_event
from .metrics import compute_metrics
from .policy import effective_settings

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "frontend" / "dist"
HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")
ACTIONS = {"interrupt", "batch", "delegate", "drop"}


class NewMessage(BaseModel):
    sender: str
    text: str
    channel: str | None = None


class Clock(BaseModel):
    time: str


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
    app = FastAPI(title="Bouncer")
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
        visible = [e for e in store.all_events() if e["time"] <= clock]
        visible.sort(key=lambda e: (e["time"], e["id"]), reverse=True)
        urgent = {k for k, items in fb.items() if any(i["kind"] == "urgent" for i in items)}
        used = sum(1 for e in visible if routed[e["id"]]["uses_budget"])
        return {
            "clock": clock, "settings": settings, "evening": clock >= settings["eveningStart"],
            "budget": {"total": settings["budget"], "left": settings["budget"] - used},
            "events": [{**e, "result": results.get(e["id"]), "decision": routed[e["id"]], "feedback": fb.get(e["id"], [])}
                       for e in visible],
            "phone": [e["id"] for e in visible if routed[e["id"]]["action"] == "interrupt" or e["id"] in urgent],
        }

    @app.get("/api/events/{event_id}")
    def event_detail(event_id: str):
        event = next((e for e in store.all_events() if e["id"] == event_id), None)
        if not event:
            raise HTTPException(404, "no such event")
        return {**event, "result": store.results().get(event_id), "decision": decisions(store)[event_id],
                "feedback": store.feedback().get(event_id, [])}

    @app.post("/api/events")
    def new_event(body: NewMessage):
        person = snapshot()["people"].get(body.sender)
        if not person or body.sender == "sanad":
            raise HTTPException(422, f"unknown sender {body.sender!r}")
        text = body.text.strip()
        if not text or len(text) > 2000:
            raise HTTPException(422, "text must be 1-2000 characters")
        event = {"type": "message", "source": "compose", "sender": body.sender, "text": text}
        if body.channel:
            event["channel"] = body.channel
        return respond(process_event(store, event, ask=ask, write=write))

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

    @app.get("/api/metrics")
    def metrics():
        return compute_metrics(store.all_events(), decisions(store), store.results(), store.get("settings"))

    @app.get("/api/digest")
    def digest():
        routed = decisions(store)
        groups = [{**g, "items": [i for i in g["items"] if (routed.get(i["event_id"]) or {}).get("action") == "batch"]}
                  for g in (store.get("digest") or {}).get("groups", [])]
        return {"groups": [g for g in groups if g["items"]]}

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
    """The app `make app` serves (uvicorn --factory): real models, data/bouncer.db, seeded on first start."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    store = Store(DB_PATH)
    if store.is_empty():
        seed_store(store)
    return create_app(store)

