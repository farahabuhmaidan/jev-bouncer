from pathlib import Path

from pipeline.load import load_events, load_snapshot
from pipeline.run import Cache, build_results

DATA = Path(__file__).resolve().parent.parent / "data"


class Fakes:
    def __init__(self, fail_jev_for=()):
        self.calls = {"jev": 0, "route": 0, "reply": 0, "explain": 0, "digest": 0}
        self.fail = set(fail_jev_for)
        self.digest_items = None

    def ask(self, state, event_type):
        self.calls["jev"] += 1
        if state.get("message") in self.fail:
            return {"answers": {}, "latency_ms": 5, "usage": {}, "request": {}, "error": "HTTP 500"}
        answers = {"needs_sanad": 0.9}
        if event_type == "ci_failure":
            regression = state["ci"]["branch"] == "investor-demo"
            answers = {"failure_type": {"code_regression": 0.9 if regression else 0.05,
                                        "flaky_test": 0.05 if regression else 0.9, "infra_problem": 0.05}}
        return {"answers": answers, "latency_ms": 5, "usage": {"cost": 1e-5}, "request": {"state": state}, "error": None}

    def route(self, state):
        self.calls["route"] += 1
        return {"action": "batch", "confidence": 0.7, "reason": "r", "latency_ms": 9, "tokens": {"in": 1, "out": 1}, "cost": 1e-3, "error": None}

    def reply(self, state, slot):
        self.calls["reply"] += 1
        return f"back at {slot}"

    def explain(self, state):
        self.calls["explain"] += 1
        return {"likely_cause": "x", "suspicious_lines": [], "suggested_fix": "y"}

    def summarize(self, items):
        self.calls["digest"] += 1
        self.digest_items = items
        return {"groups": []}

    def kw(self):
        return dict(ask=self.ask, route=self.route, reply=self.reply, explain=self.explain, summarize=self.summarize)


def _day():
    snap = load_snapshot(DATA / "snapshot.json")
    return snap, load_events(DATA / "events.json", snap)


def test_results_shape(tmp_path):
    snap, events = _day()
    r = build_results(snap, events, cache=Cache(tmp_path), **Fakes().kw())
    assert set(r) >= {"generated_at", "models", "day", "events", "digest"}
    assert r["models"] == {"jev": "typesafe/jev-1.14", "llm": "anthropic/claude-sonnet-5.5"}
    assert len(r["day"]["events"]) == len(events) and r["day"]["snapshot"]["calendar"]
    e = r["events"]["evt-015"]
    assert set(e) >= {"state", "jev", "baseline", "auto_reply", "ci_explanation", "next_free_slot"}
    assert e["jev"]["answers"]["needs_sanad"] == 0.9 and e["baseline"]["action"] == "batch"


def test_auto_reply_only_for_people(tmp_path):
    snap, events = _day()
    r = build_results(snap, events, cache=Cache(tmp_path), **Fakes().kw())
    assert r["events"]["evt-015"]["auto_reply"] == "back at 16:00"  # Rami, person
    assert r["events"]["evt-001"]["auto_reply"] is None              # newsletter bot
    assert r["events"]["evt-016"]["auto_reply"] is None              # CI


def test_ci_explain_only_when_jev_says_regression(tmp_path):
    snap, events = _day()
    f = Fakes()
    r = build_results(snap, events, cache=Cache(tmp_path), **f.kw())
    assert r["events"]["evt-018"]["ci_explanation"] and r["events"]["evt-016"]["ci_explanation"] is None
    assert f.calls["explain"] == 1


def test_digest_covers_messages_from_people(tmp_path):
    snap, events = _day()
    f = Fakes()
    build_results(snap, events, cache=Cache(tmp_path), **f.kw())
    ids = {i["id"] for i in f.digest_items}
    assert {"evt-014", "evt-005", "evt-015"} <= ids
    assert "evt-001" not in ids and "evt-016" not in ids  # bots and CI are not in the digest


def test_cache_hit_skips_calls_and_text_change_misses(tmp_path):
    snap, events = _day()
    build_results(snap, events, cache=Cache(tmp_path), **Fakes().kw())
    f2 = Fakes()
    build_results(snap, events, cache=Cache(tmp_path), **f2.kw())
    assert f2.calls == {"jev": 0, "route": 0, "reply": 0, "explain": 0, "digest": 0}
    changed = [dict(e, text=e["text"] + "!") if e["id"] == "evt-010" else e for e in events]
    f3 = Fakes()
    build_results(snap, changed, cache=Cache(tmp_path), **f3.kw())
    assert f3.calls["jev"] == 1 and f3.calls["route"] == 1


def test_error_recorded_not_cached(tmp_path):
    snap, events = _day()
    r = build_results(snap, events, cache=Cache(tmp_path), **Fakes(fail_jev_for={"lunch? 🌯"}).kw())
    assert r["events"]["evt-010"]["jev"]["error"] == "HTTP 500" and r["events"]["evt-010"]["jev"]["answers"] == {}
    f2 = Fakes()
    build_results(snap, events, cache=Cache(tmp_path), **f2.kw())
    assert f2.calls["jev"] == 1  # the failed call is retried on the next run


def test_offline_uses_cache_only(tmp_path):
    snap, events = _day()
    r = build_results(snap, events, cache=Cache(tmp_path), offline=True, **Fakes().kw())
    assert r["events"]["evt-015"]["jev"]["error"].startswith("not in cache")


def test_prune_removes_entries_the_run_did_not_use(tmp_path):
    snap, events = _day()
    build_results(snap, events, cache=Cache(tmp_path), **Fakes().kw())
    (tmp_path / "baseline-evt-999-stale.json").write_text("{}")
    cache = Cache(tmp_path)
    build_results(snap, events, cache=cache, **Fakes().kw())
    removed = cache.prune()
    assert removed == 1 and not (tmp_path / "baseline-evt-999-stale.json").exists()
    f = Fakes()
    build_results(snap, events, cache=Cache(tmp_path), **f.kw())
    assert f.calls["jev"] == 0


def test_llm_cache_keys_cover_model_schema_tokens_effort(monkeypatch):
    from pipeline import llm
    from pipeline.run import llm_key_parts
    base = Cache.key("baseline", "e", *llm_key_parts(llm.BASELINE_SYSTEM, llm.BASELINE_SCHEMA, llm.BASELINE_PARAMS), {})
    for change in [lambda: monkeypatch.setattr(llm, "LLM_MODEL", "other/model"),
                   lambda: monkeypatch.setitem(llm.BASELINE_PARAMS, "max_tokens", 1),
                   lambda: monkeypatch.setitem(llm.BASELINE_PARAMS, "effort", "high"),
                   lambda: monkeypatch.setattr(llm, "BASELINE_SCHEMA", {"x": 1})]:
        change()
        assert Cache.key("baseline", "e", *llm_key_parts(llm.BASELINE_SYSTEM, llm.BASELINE_SCHEMA, llm.BASELINE_PARAMS), {}) != base
        monkeypatch.undo()
