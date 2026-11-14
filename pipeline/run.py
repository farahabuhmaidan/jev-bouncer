"""Offline pipeline: one pass over the day, writes web/results.json (design/01-architecture.md).

    python -m pipeline.run              # call Jev and the LLM for anything not cached
    python -m pipeline.run --eval-only  # rebuild results.json from the cache, no network

The pipeline never decides what happens to an event. It records Jev's answers, the
LLM-only baseline and the text the LLM writes; the policy runs in the browser.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from . import llm
from .adapters.base import DEMO_TZ
from .jev import JEV_MODEL, ask_jev
from .load import load_events, load_snapshot
from .prices import PRICES
from .questions import questions_for
from .state import build_state, next_free_slot

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "pipeline" / "cache"
WORKERS = 4


class Cache:
    """One JSON file per call, keyed by kind + event id + a hash of everything the call sends.
    Errors are never cached, so a failed call is retried on the next run."""

    def __init__(self, directory: Path = CACHE_DIR):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.used: set[str] = set()

    @staticmethod
    def key(kind: str, event_id: str, *parts) -> str:
        digest = hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
        return f"{kind}-{event_id}-{digest}"

    def get(self, key: str):
        self.used.add(key)
        path = self.dir / f"{key}.json"
        return json.loads(path.read_text()) if path.exists() else None

    def prune(self) -> int:
        """Delete entries this run did not touch (old prompts, reworded events). Returns how many."""
        stale = [f for f in self.dir.glob("*.json") if f.stem not in self.used]
        for f in stale:
            f.unlink()
        return len(stale)

    def put(self, key: str, value) -> None:
        self.used.add(key)
        (self.dir / f"{key}.json").write_text(json.dumps(value, ensure_ascii=False, indent=1))


def _is_error(value) -> bool:
    return value is None or (isinstance(value, dict) and value.get("error"))


def _cached(cache: Cache, key: str, call, offline: bool, miss):
    """Return the cached value, or make the call (retrying once on error) and cache a success."""
    hit = cache.get(key)
    if hit is not None:
        return hit
    if offline:
        return miss
    value = call()
    if _is_error(value):
        value = call()
    if not _is_error(value):
        cache.put(key, value)
    return value


def _safe(fn, *args):
    """LLM writing jobs raise on failure; record None and say so instead of crashing the run."""
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001 - any failure is reported, never turned into text
        print(f"  ! {fn.__name__} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None


def _from_person(event: dict, snapshot: dict) -> bool:
    if event["type"] != "message" or event["sender"].startswith("unknown:"):
        return False
    return not snapshot["people"][event["sender"]].get("is_bot")


def _top(choice: dict) -> str | None:
    return max(choice, key=choice.get) if choice else None


def llm_key_parts(system: str, schema: dict | None, params: dict) -> tuple:
    """Everything an LLM call sends besides its input: model, prompt, schema, max_tokens, effort."""
    return (llm.LLM_MODEL, system, schema, params)


def _one_event(event, snapshot, cache, offline, ask, route, reply, explain) -> dict:
    eid, etype = event["id"], event["type"]
    state = build_state(event, snapshot)
    slot = next_free_slot(event["time"], snapshot)
    not_cached = {"answers": {}, "latency_ms": None, "usage": {}, "request": {},
                  "error": "not in cache (run without --eval-only)"}

    jev = _cached(cache, Cache.key("jev", eid, JEV_MODEL, state, questions_for(etype)),
                  lambda: ask(state, etype), offline, not_cached)
    baseline = _cached(cache, Cache.key("baseline", eid, *llm_key_parts(llm.BASELINE_SYSTEM, llm.BASELINE_SCHEMA, llm.BASELINE_PARAMS), state),
                       lambda: route(state), offline,
                       {"action": None, "confidence": None, "reason": None, "error": not_cached["error"]})

    auto_reply = None
    if _from_person(event, snapshot):
        auto_reply = _cached(cache, Cache.key("reply", eid, *llm_key_parts(llm.AUTO_REPLY_SYSTEM, None, llm.REPLY_PARAMS), state, slot),
                             lambda: _safe(reply, state, slot), offline, None)

    ci_explanation = None
    if etype == "ci_failure" and _top(jev.get("answers", {}).get("failure_type", {})) == "code_regression":
        ci_explanation = _cached(cache, Cache.key("explain", eid, *llm_key_parts(llm.CI_SYSTEM, llm.CI_SCHEMA, llm.CI_PARAMS), state),
                                 lambda: _safe(explain, state), offline, None)

    return {"state": state, "jev": jev, "baseline": baseline, "auto_reply": auto_reply,
            "ci_explanation": ci_explanation, "next_free_slot": slot}


def build_results(snapshot: dict, events: list[dict], cache: Cache | None = None, offline: bool = False,
                  ask=ask_jev, route=llm.baseline_route, reply=llm.auto_reply, explain=llm.ci_explain,
                  summarize=llm.digest) -> dict:
    cache = cache or Cache()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        outs = list(pool.map(lambda e: _one_event(e, snapshot, cache, offline, ask, route, reply, explain), events))
    per_event = {e["id"]: out for e, out in zip(events, outs)}

    # The digest covers every message from a person; the page shows the ones the current settings held back.
    items = [{"id": e["id"], "time": e["time"], "sender": per_event[e["id"]]["state"]["sender"], "text": e["text"]}
             for e in events if _from_person(e, snapshot)]
    digest = _cached(cache, Cache.key("digest", "day", *llm_key_parts(llm.DIGEST_SYSTEM, llm.DIGEST_SCHEMA, llm.DIGEST_PARAMS), items),
                     lambda: _safe(summarize, items), offline, None) or {"groups": []}

    return {
        "generated_at": datetime.now(DEMO_TZ).isoformat(timespec="seconds"),
        "models": {"jev": JEV_MODEL, "llm": llm.LLM_MODEL},
        "day": {"snapshot": snapshot, "events": events},
        "events": per_event,
        "digest": digest,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--eval-only", action="store_true", help="rebuild from the cache without calling any model")
    parser.add_argument("--out", default=str(ROOT / "web" / "results.json"))
    args = parser.parse_args(argv)
    if not args.eval_only:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")

    snapshot = load_snapshot(ROOT / "data" / "snapshot.json")
    events = load_events(ROOT / "data" / "events.json", snapshot)
    cache = Cache()
    results = build_results(snapshot, events, cache=cache, offline=args.eval_only)
    if args.eval_only and Path(args.out).exists():  # a rebuild keeps the date of the run it came from
        results["generated_at"] = json.loads(Path(args.out).read_text())["generated_at"]
    if not args.eval_only:
        print(f"pruned {cache.prune()} stale cache entries")
    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=1))
    (Path(args.out).parent / "prices.json").write_text(json.dumps(PRICES, indent=1))

    errors = [eid for eid, r in results["events"].items() if r["jev"].get("error") or r["baseline"].get("error")]
    print(f"wrote {args.out}: {len(events)} events, {len(errors)} with errors {errors if errors else ''}")


if __name__ == "__main__":
    main()
