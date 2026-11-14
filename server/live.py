"""Live events (design/14-app.md § Backend): state → Jev → policy now; LLM text in the background."""
from __future__ import annotations

import threading

from pipeline import llm
from pipeline.jev import ask_jev
from datetime import date

from pipeline.state import build_state, deadline_minutes, next_free_slot
from pipeline.when import resolve_when

from .db import Store
from .calendar import TODAY, clashes, next_free
from .google import GoogleError
from .policy import effective_settings, replay_day

REMINDER_MINUTES = 30


def _thread(fn):
    threading.Thread(target=fn, daemon=True).start()


def with_settings(snapshot: dict, settings: dict) -> dict:
    """The snapshot as Sanad configured it: people in settings.family are family, nobody else is.
    Seeded events keep their cached answers; this shapes the state of new events."""
    family = set(settings.get("family", []))
    people = {}
    for k, p in snapshot["people"].items():
        if p.get("is_bot") or k == "sanad":
            people[k] = p
        elif k in family:
            people[k] = {**p, "relationship": "family"}
        elif p.get("relationship") == "family":
            people[k] = {**p, "relationship": "contact"}
        else:
            people[k] = p
    return {**snapshot, "people": people}


def _is_person(event: dict, snapshot: dict) -> bool:
    p = snapshot["people"].get(event["sender"])
    return event["type"] == "message" and bool(p) and not p.get("is_bot")


def decisions(store: Store, source: str = "jev") -> dict:
    """The whole day routed from one answer source; live events have no baseline, so theirs is an error."""
    return replay_day(store.all_events(), store.results(), store.get("snapshot"), store.get("settings"), source)


def baseline_decisions(store: Store) -> dict:
    """The baseline's answers through the same policy; None for events the baseline never saw (live)."""
    results = store.results()
    routed = decisions(store, "baseline")
    return {eid: (d if (results.get(eid) or {}).get("baseline") else None) for eid, d in routed.items()}


def place_reminder(when: dict, title: str, p: float, events_on=None) -> dict:
    """The reminder at the time the message implies, with any clashes and the next free start.
    `events_on(day)` is the calendar to check: the demo one, or Google Calendar when connected."""
    hit = clashes(when["date"], when["time"], REMINDER_MINUTES, events_on)
    return {**when, "title": title, "minutes": REMINDER_MINUTES, "p": p, "status": "added", "clashes": hit,
            "suggested": next_free(when["date"], when["time"], REMINDER_MINUTES, source=events_on) if hit else None}


def _reminder(event: dict, state: dict, clock: str, ask, settings: dict, events_on=None) -> dict | None:
    """Code finds a future date; Jev says whether Sanad has a task then; code adds the reminder."""
    when = resolve_when(event.get("text", ""), date.fromisoformat(TODAY), clock) if event["type"] == "message" else None
    if not when:
        return None
    rj = ask(state, "reminder")
    if rj.get("error"):
        rj = ask(state, "reminder")
    if rj.get("error"):
        return {**when, "status": "error", "error": rj["error"]}
    p = (rj.get("answers") or {}).get("task_later")
    if not isinstance(p, (int, float)) or p < effective_settings(settings)["yesAt"]:
        return None
    text = event["text"].strip()
    try:
        return place_reminder(when, text if len(text) <= 60 else text[:57] + "…", p, events_on)
    except GoogleError as e:  # the calendar couldn't be checked: say so, never pretend it's free
        return {**when, "status": "error", "error": f"couldn't check your calendar: {e}"}


def process_event(store: Store, event: dict, ask=ask_jev, write=True, run=_thread,
                  reply=llm.auto_reply, explain=llm.ci_explain, title=llm.reminder_title,
                  at: str | None = None, dry_run: bool = False, events_on=None) -> dict:
    """Store a new event stamped with the demo clock (or `at`), route it, and (if write) let the LLM write
    its text. A dry run routes it against the real day, writes the text inline, then removes it again."""
    snapshot = with_settings(store.get("snapshot"), effective_settings(store.get("settings")))
    clock = at or store.get("clock")
    if dry_run:
        run = lambda fn: fn()  # noqa: E731  the caller waits for the full response
    event = {**event, "id": store.next_live_id(), "time": clock, "label": None, "holdout": False,
             "demo_moment": None, **({"source_time": event["time"]} if event.get("time") else {})}
    state = build_state(event, snapshot)
    jev = ask(state, event["type"])
    if jev.get("error"):
        jev = ask(state, event["type"])
    reminder = None if jev.get("error") else _reminder(event, state, clock, ask, store.get("settings"), events_on)
    result = {"state": state, "facts": {"deadline_in_minutes": deadline_minutes(event, snapshot)}, "jev": jev,
              "baseline": None, "auto_reply": None, "ci_explanation": None, "reminder": reminder,
              "next_free_slot": next_free_slot(clock, snapshot), "writing": False}
    store.add_event(event, result, origin="live")
    decision = decisions(store)[event["id"]]

    wants_reply = decision["action"] == "batch" and _is_person(event, snapshot)
    ft = (jev.get("answers") or {}).get("failure_type") or {}
    wants_explain = event["type"] == "ci_failure" and ft and max(ft, key=ft.get) == "code_regression"
    wants_title = bool(reminder) and reminder["status"] == "added"
    if write and (wants_reply or wants_explain or wants_title):
        store.set_result(event["id"], {"writing": True})
        result["writing"] = True

        def work():
            patch = {"writing": False}
            try:
                if wants_reply:
                    patch["auto_reply"] = reply(state, result["next_free_slot"])
                if wants_explain:
                    patch["ci_explanation"] = explain(state)
                if wants_title:
                    current = store.results()[event["id"]].get("reminder") or reminder
                    patch["reminder"] = {**current, "title": title(state)}
            except Exception as exc:  # noqa: BLE001 - shown in the UI, never turned into text
                patch["llm_error"] = f"{type(exc).__name__}: {exc}"
            store.set_result(event["id"], patch)
        run(work)

    out = {"event": {**event, "origin": "live"}, "result": store.results()[event["id"]], "decision": decision,
           "baseline_decision": None, "dry_run": dry_run}
    if dry_run:
        store.delete_event(event["id"])
    return out
