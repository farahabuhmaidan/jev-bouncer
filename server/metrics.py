"""Jev vs the baseline LLM, both through the same policy (design/08-evaluation.md).
Only labelled events count; an "ask" or an error is wrong in accuracy. Cost is the mean measured `usage.cost` per call x 1000."""
from __future__ import annotations

import json
import math

from .policy import DEFAULTS

_ALIASES = {"rerun silently": "drop", "pinged DevOps": "delegate"}
_MISSES = {"batch", "drop", "delegate"}


def normalize_action(a):
    return _ALIASES.get(a, a)


def _share(hits, n):
    return hits / n if n else None


def _quantile(values, q):
    xs = sorted(v for v in values if isinstance(v, (int, float)))
    if not xs:
        return None
    return xs[min(len(xs) - 1, max(0, math.ceil(q * len(xs)) - 1))]


def _cost_per_1k(costs):
    xs = [c for c in costs if isinstance(c, (int, float))]
    return sum(xs) / len(xs) * 1000 if xs else None


def _score(events, action_of):
    act = lambda e: normalize_action(action_of(e))  # noqa: E731
    right = lambda e: act(e) == e["label"]["action"]  # noqa: E731
    acc = lambda xs: _share(sum(map(right, xs)), len(xs))  # noqa: E731
    interrupted = [e for e in events if act(e) == "interrupt"]
    precision = _share(sum(e["label"]["action"] == "interrupt" for e in interrupted), len(interrupted))
    return {
        "critical_misses": sum(1 for e in events if e["label"]["action"] == "interrupt" and act(e) in _MISSES),
        "precision": precision,
        "false_alarm_rate": None if precision is None else 1 - precision,
        "accuracy": acc(events),
        "accuracy_excl_asks": acc([e for e in events if act(e) != "ask"]),
        "holdout_accuracy": acc([e for e in events if e.get("holdout")]),
        "by_type": {"message": acc([e for e in events if e["type"] == "message"]),
                    "ci": acc([e for e in events if e["type"] == "ci_failure"])},
        "asks": sum(act(e) == "ask" for e in events),
        "errors": sum(act(e) == "error" for e in events),
    }


def settings_differ(settings: dict | None) -> bool:
    settings = settings or {}
    return any(k in settings and json.dumps(settings[k]) != json.dumps(v) for k, v in DEFAULTS.items())


def compute_metrics(events, decisions, results, settings=None, baseline=None) -> dict:
    """`decisions` routes Jev's answers, `baseline` routes the baseline's answers, both through the
    same policy at the same settings (server/policy.replay_day with source="jev" / "baseline")."""
    labelled = [e for e in events if (e.get("label") or {}).get("action")]
    baseline = baseline or {}
    jev_action = lambda e: (decisions.get(e["id"]) or {}).get("action") or "error"  # noqa: E731
    llm_action = lambda e: (baseline.get(e["id"]) or {}).get("action") or "error"  # noqa: E731
    jev = [(results.get(e["id"]) or {}).get("jev") or {} for e in labelled]
    llm = [(results.get(e["id"]) or {}).get("baseline") or {} for e in labelled]
    return {
        "jev": {**_score(labelled, jev_action),
                "p50": _quantile([r.get("latency_ms") for r in jev], 0.5),
                "p95": _quantile([r.get("latency_ms") for r in jev], 0.95),
                "cost_per_1k": _cost_per_1k([(r.get("usage") or {}).get("cost") for r in jev])},
        "llm": {**_score(labelled, llm_action),
                "p50": _quantile([r.get("latency_ms") for r in llm], 0.5),
                "p95": _quantile([r.get("latency_ms") for r in llm], 0.95),
                "cost_per_1k": _cost_per_1k([r.get("cost") for r in llm])},
        "settings_changed": settings_differ(settings),
        "n": len(labelled),
    }
