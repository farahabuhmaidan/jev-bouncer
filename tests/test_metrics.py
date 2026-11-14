import json
from pathlib import Path

import pytest

from server.metrics import compute_metrics, normalize_action
from server.policy import DEFAULTS, replay_day

ROOT = Path(__file__).resolve().parent.parent


def ev(id, type, action, holdout=False):
    return {"id": id, "type": type, "label": {"action": action}, "holdout": holdout}


def res(llm_action, cost=1e-5, llm_cost=2e-3, lat=100, llm_lat=2000):
    return {"jev": {"answers": {}, "latency_ms": lat, "usage": {"cost": cost}, "error": None},
            "baseline": {"action": llm_action, "latency_ms": llm_lat, "cost": llm_cost, "error": None}}


EVENTS = [ev("a", "message", "interrupt"), ev("b", "message", "batch", True),
          ev("c", "ci_failure", "drop"), ev("d", "ci_failure", "delegate", True)]
RESULTS = {"a": res("batch"), "b": res("batch"), "c": res("drop"), "d": res("interrupt")}


def dec(**actions):
    return {k: {"action": v} for k, v in actions.items()}


def test_toy_set_accuracy_and_critical_misses():
    m = compute_metrics(EVENTS, dec(a="interrupt", b="batch", c="drop", d="batch"), RESULTS)
    assert m["jev"]["accuracy"] == 0.75 and m["jev"]["holdout_accuracy"] == 0.5
    assert m["jev"]["by_type"] == {"message": 1, "ci": 0.5} and m["jev"]["critical_misses"] == 0
    assert m["llm"]["accuracy"] == 0.5 and m["llm"]["critical_misses"] == 1


def test_ask_counts_wrong_and_counted():
    m = compute_metrics(EVENTS, dec(a="ask", b="batch", c="drop", d="delegate"), RESULTS)
    assert m["jev"]["accuracy"] == 0.75 and m["jev"]["asks"] == 1 and m["jev"]["critical_misses"] == 0


def test_error_counts_wrong_and_counted():
    m = compute_metrics(EVENTS, dec(a="error", b="batch", c="drop", d="delegate"), RESULTS)
    assert m["jev"]["accuracy"] == 0.75 and m["jev"]["errors"] == 1


def test_cost_per_1k_from_measured_cost():
    m = compute_metrics(EVENTS, dec(), RESULTS)
    assert m["jev"]["cost_per_1k"] == pytest.approx(0.01) and m["llm"]["cost_per_1k"] == pytest.approx(2)


def test_cost_null_when_unmeasured():
    bare = {k: res("batch", cost=None, llm_cost=None) for k in RESULTS}
    assert compute_metrics(EVENTS, dec(), bare)["jev"]["cost_per_1k"] is None


def test_latency_nearest_rank():
    r = {k: res("batch", lat=v) for k, v in zip("abcd", [100, 200, 300, 400])}
    m = compute_metrics(EVENTS, dec(), r)
    assert (m["jev"]["p50"], m["jev"]["p95"]) == (200, 400)


def test_settings_changed():
    assert compute_metrics(EVENTS, dec(), RESULTS, {"budget": 3})["settings_changed"] is True
    assert compute_metrics(EVENTS, dec(), RESULTS)["settings_changed"] is False


def test_unlabelled_live_events_ignored():
    m = compute_metrics(EVENTS + [{"id": "live-1", "type": "message", "label": None, "holdout": False}], dec(a="interrupt"), RESULTS)
    assert m["llm"]["accuracy"] == 0.5


def test_ci_aliases():
    assert normalize_action("rerun silently") == "drop" and normalize_action("pinged DevOps") == "delegate"


def test_metrics_match_first_build():
    r = json.loads((ROOT / "web" / "results.json").read_text())
    events, snap = r["day"]["events"], r["day"]["snapshot"]
    m = compute_metrics(events, replay_day(events, r["events"], snap, DEFAULTS), r["events"])
    assert round(m["jev"]["accuracy"] * 100) == 64 and round(m["llm"]["accuracy"] * 100) == 76
    assert (m["jev"]["critical_misses"], m["llm"]["critical_misses"], m["jev"]["asks"]) == (1, 3, 7)
