import json
from pathlib import Path

import pytest

from server.metrics import compute_metrics, normalize_action
from server.policy import DEFAULTS, replay_day

ROOT = Path(__file__).resolve().parent.parent


def ev(id, type, action, holdout=False):
    return {"id": id, "type": type, "label": {"action": action}, "holdout": holdout}


def res(cost=1e-5, llm_cost=2e-3, lat=100, llm_lat=2000):
    return {"jev": {"answers": {}, "latency_ms": lat, "usage": {"cost": cost}, "error": None},
            "baseline": {"answers": {}, "latency_ms": llm_lat, "cost": llm_cost, "error": None}}


EVENTS = [ev("a", "message", "interrupt"), ev("b", "message", "batch", True),
          ev("c", "ci_failure", "drop"), ev("d", "ci_failure", "delegate", True)]
RESULTS = {k: res() for k in "abcd"}


def dec(**actions):
    return {k: {"action": v} for k, v in actions.items()}


BASE = dec(a="batch", b="batch", c="drop", d="interrupt")


def test_toy_set_accuracy_and_critical_misses():
    m = compute_metrics(EVENTS, dec(a="interrupt", b="batch", c="drop", d="batch"), RESULTS, baseline=BASE)
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
    bare = {k: res(cost=None, llm_cost=None) for k in RESULTS}
    assert compute_metrics(EVENTS, dec(), bare)["jev"]["cost_per_1k"] is None


def test_latency_nearest_rank():
    r = {k: res(lat=v) for k, v in zip("abcd", [100, 200, 300, 400])}
    m = compute_metrics(EVENTS, dec(), r)
    assert (m["jev"]["p50"], m["jev"]["p95"]) == (200, 400)


def test_settings_changed():
    assert compute_metrics(EVENTS, dec(), RESULTS, {"budget": 3})["settings_changed"] is True
    assert compute_metrics(EVENTS, dec(), RESULTS)["settings_changed"] is False


def test_unlabelled_live_events_ignored():
    m = compute_metrics(EVENTS + [{"id": "live-1", "type": "message", "label": None, "holdout": False}], dec(a="interrupt"), RESULTS, baseline=BASE)
    assert m["llm"]["accuracy"] == 0.5


def test_ci_aliases():
    assert normalize_action("rerun silently") == "drop" and normalize_action("pinged DevOps") == "delegate"


def test_interrupt_precision_and_false_alarms():
    m = compute_metrics(EVENTS, dec(a="interrupt", b="interrupt", c="drop", d="batch"), RESULTS, baseline=BASE)
    assert m["jev"]["precision"] == 0.5 and m["jev"]["false_alarm_rate"] == 0.5
    assert m["llm"]["precision"] == 0 and m["llm"]["false_alarm_rate"] == 1


def test_precision_none_without_interrupts():
    assert compute_metrics(EVENTS, dec(a="batch"), RESULTS)["jev"]["precision"] is None


def test_accuracy_excluding_asks_and_asks_per_source():
    m = compute_metrics(EVENTS, dec(a="ask", b="batch", c="drop", d="delegate"), RESULTS,
                        baseline=dec(a="ask", b="ask", c="drop", d="batch"))
    assert m["jev"]["accuracy_excl_asks"] == 1 and m["jev"]["asks"] == 1
    assert m["llm"]["accuracy_excl_asks"] == 0.5 and m["llm"]["asks"] == 2


def test_baseline_error_counts_wrong():
    m = compute_metrics(EVENTS, dec(), RESULTS, baseline=dec(a="error", b="batch", c="drop", d="delegate"))
    assert m["llm"]["errors"] == 1 and m["llm"]["accuracy"] == 0.75


def test_metrics_on_the_committed_results():
    """Both answer sets through the same policy at default settings (README numbers)."""
    r = json.loads((ROOT / "data" / "results.json").read_text())
    events, snap = r["day"]["events"], r["day"]["snapshot"]
    m = compute_metrics(events, replay_day(events, r["events"], snap, DEFAULTS), r["events"],
                        baseline=replay_day(events, r["events"], snap, DEFAULTS, source="baseline"))
    assert m["n"] == len(events) and m["jev"]["errors"] == 0 and m["llm"]["errors"] == 0
