"""Live events (design/14-app.md § Backend): state → Jev → policy now; LLM text in the background."""
from __future__ import annotations

import threading

from pipeline import llm
from pipeline.jev import ask_jev
from pipeline.state import build_state, next_free_slot

from .db import Store
from .policy import replay_day


def _thread(fn):
    threading.Thread(target=fn, daemon=True).start()


def _is_person(event: dict, snapshot: dict) -> bool:
    p = snapshot["people"].get(event["sender"])
    return event["type"] == "message" and bool(p) and not p.get("is_bot")


def decisions(store: Store) -> dict:
    return replay_day(store.all_events(), store.results(), store.get("snapshot"), store.get("settings"))


def process_event(store: Store, event: dict, ask=ask_jev, write=True, run=_thread,
                  reply=llm.auto_reply, explain=llm.ci_explain) -> dict:
    """Store a new event stamped with the demo clock, route it, and (if write) let the LLM write its text."""
    snapshot = store.get("snapshot")
    clock = store.get("clock")
    event = {**event, "id": store.next_live_id(), "time": clock, "label": None, "holdout": False,
             "demo_moment": None, **({"source_time": event["time"]} if event.get("time") else {})}
    state = build_state(event, snapshot)
    jev = ask(state, event["type"])
    if jev.get("error"):
        jev = ask(state, event["type"])
    result = {"state": state, "jev": jev, "baseline": None, "auto_reply": None, "ci_explanation": None,
              "next_free_slot": next_free_slot(clock, snapshot), "writing": False}
    store.add_event(event, result, origin="live")
    decision = decisions(store)[event["id"]]

    wants_reply = decision["action"] == "batch" and _is_person(event, snapshot)
    ft = (jev.get("answers") or {}).get("failure_type") or {}
    wants_explain = event["type"] == "ci_failure" and ft and max(ft, key=ft.get) == "code_regression"
    if write and (wants_reply or wants_explain):
        store.set_result(event["id"], {"writing": True})
        result["writing"] = True

        def work():
            patch = {"writing": False}
            try:
                if wants_reply:
                    patch["auto_reply"] = reply(state, result["next_free_slot"])
                if wants_explain:
                    patch["ci_explanation"] = explain(state)
            except Exception as exc:  # noqa: BLE001 - shown in the UI, never turned into text
                patch["llm_error"] = f"{type(exc).__name__}: {exc}"
            store.set_result(event["id"], patch)
        run(work)

    return {"event": {**event, "origin": "live"}, "result": store.results()[event["id"]], "decision": decision}
