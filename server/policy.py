"""Routing policy (design/04-policy.md). Jev answers the judgments; this module decides.

The only routing code in the app. Settings keys are camelCase because they are the JSON
contract with the frontend.
"""
from __future__ import annotations

import re

DEFAULTS = {
    "yesAt": 0.7, "noAt": 0.3, "interruptBar": 0.7, "risingBar": True, "budget": 5,
    "eveningStart": "18:00", "familyAlways": True, "silentRerun": True,
    "family": ["maha", "school"], "vip": [], "deadlineMinutes": 120,
}
MORNING = "until 09:00 tomorrow"
_HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


def _num(v, default, lo, hi):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi else default


def effective_settings(settings: dict | None) -> dict:
    """Merge with defaults, replace malformed values with the default, keep the sure band valid."""
    s = {**DEFAULTS, **(settings or {})}
    for k, lo, hi in [("yesAt", 0, 1), ("noAt", 0, 1), ("interruptBar", 0, 1)]:
        s[k] = _num(s[k], DEFAULTS[k], lo, hi)
    s["budget"] = int(_num(s["budget"], DEFAULTS["budget"], 0, 50))
    s["deadlineMinutes"] = int(_num(s["deadlineMinutes"], DEFAULTS["deadlineMinutes"], 15, 480))
    for k in ("risingBar", "familyAlways", "silentRerun"):
        if not isinstance(s[k], bool):
            s[k] = DEFAULTS[k]
    if not isinstance(s["eveningStart"], str) or not _HHMM.fullmatch(s["eveningStart"]):
        s["eveningStart"] = DEFAULTS["eveningStart"]
    for k in ("family", "vip"):
        if not isinstance(s[k], list) or not all(isinstance(x, str) for x in s[k]):
            s[k] = list(DEFAULTS[k])
    if s["yesAt"] <= s["noAt"]:
        s["noAt"] = s["yesAt"] - 0.05
    return s


def rising_bar(s: dict, budget_left: int) -> float:
    if not s["risingBar"]:
        return s["interruptBar"]
    return min(0.95, s["interruptBar"] + 0.15 * (s["budget"] - budget_left) / max(1, s["budget"] - 1))


class _Reader:
    """Reads Jev answers against the sure band and records which ones a rule looked at."""

    def __init__(self, answers: dict, s: dict):
        self.answers, self.s, self.reasons = answers, s, []

    def p(self, q):
        v = self.answers.get(q)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return None
        if not any(r["q"] == q for r in self.reasons):
            self.reasons.append({"q": q, "p": v})
        return v

    def yes(self, q):
        v = self.p(q)
        return v is not None and v >= self.s["yesAt"]

    def no(self, q):
        v = self.p(q)
        return v is not None and v <= self.s["noAt"]

    def unsure(self, q):
        v = self.p(q)
        return v is None or self.s["noAt"] < v < self.s["yesAt"]


def _out(r, action, rule, **extra):
    return {"action": action, "rule": rule, "reasons": r.reasons, "uses_budget": False, **extra}


def _delegate_to(event, snapshot):
    people = snapshot.get("people", {})
    lead_key = (people.get(event["sender"]) or {}).get("lead")
    lead = people.get(lead_key) if lead_key and lead_key != "sanad" else None
    return f"forwarded to {lead['name']}" if lead else "forwarded to the team channel"


def _decide_message(event, r, s, day):
    later = MORNING if day["evening"] else f"until {day.get('next_slot') or 'the next free slot'}"
    people = day["snapshot"].get("people", {})

    family = event["sender"] in s["family"] or r.yes("family_matter")
    deadline = day.get("deadline")
    # Row 5 is checked here so evening mode (row 2) can step aside for it; it applies after rows 3-4.
    deadline_soon = deadline is not None and deadline < s["deadlineMinutes"]
    if s["familyAlways"] and family:
        # Family can always reach Sanad, past the budget and evening mode, but only when it can't wait.
        # Family that can wait is held for his next free slot: never asked about or forwarded.
        return _out(r, "batch", 1, label=later) if r.no("time_sensitive") else _out(r, "interrupt", 1)
    if day["evening"] and not family and not r.yes("blocks_release") and not (deadline_soon and r.no("is_noise")):
        return _out(r, "batch", 2, label=MORNING)
    if r.yes("is_noise"):
        return _out(r, "drop", 3)
    if r.yes("blocks_release") and r.yes("needs_sanad"):
        return _out(r, "interrupt", 4)
    if deadline_soon and r.no("is_noise"):
        # A deadline the clock can read beats wording and budget; it never spends budget.
        r.reasons.append({"q": "deadline_in_minutes", "value": deadline})
        return _out(r, "interrupt", 5)
    if r.yes("wording_only_urgency") and not r.yes("blocks_release"):
        return _out(r, "batch", 6, label=later)
    if r.unsure("needs_sanad"):
        return _out(r, "ask", 7)
    if r.no("needs_sanad"):
        # Leadership asked Sanad directly: hold it for him rather than forwarding it.
        if (people.get(event["sender"]) or {}).get("relationship") == "leadership":
            return _out(r, "batch", 8, label=later)
        return _out(r, "delegate", 8, label=_delegate_to(event, day["snapshot"]))
    # Timing only matters once Sanad is needed, so an unsure time_sensitive asks only here.
    if r.unsure("time_sensitive"):
        return _out(r, "ask", 7)
    vip = event["sender"] in s["vip"]
    if r.yes("time_sensitive") and (vip or day["budget_left"] >= 1) and r.p("time_sensitive") >= day["bar"]:
        return _out(r, "interrupt", 9, uses_budget=not vip)
    return _out(r, "batch", 10, label=later)


def _top(dist):
    return max(dist, key=dist.get) if isinstance(dist, dict) and dist else None


def _decide_ci(event, r, s, day, answers):
    kind = _top(answers.get("failure_type"))
    if kind:
        r.reasons.append({"q": "failure_type", "p": answers["failure_type"][kind], "value": kind})
    if kind == "code_regression" and r.yes("blocks_release"):
        return _out(r, "interrupt", "ci-regression-blocks", label="explanation attached")
    if day["evening"]:
        return _out(r, "batch", "ci-evening", label=MORNING)
    if r.no("cause_identifiable"):
        action = "batch" if r.no("blocks_release") else "interrupt"
        return _out(r, action, "ci-unclear", label="unclear failure")
    if kind == "flaky_test":
        return _out(r, "drop", "ci-flaky", label="rerun silently") if s["silentRerun"] else _out(r, "batch", "ci-flaky")
    if kind == "infra_problem":
        devops = day["snapshot"].get("people", {}).get(day["snapshot"].get("devops_contact"))
        return _out(r, "delegate", "ci-infra", label=f"pinged DevOps ({devops['name']})" if devops else "pinged DevOps")
    if kind == "config_or_lint":
        return _out(r, "batch", "ci-lint")
    return _out(r, "batch", "ci-regression", label="explanation in the digest")


def decide(event: dict, answers_result: dict | None, settings: dict, day: dict) -> dict:
    """Route one event from one answer set (Jev's or the baseline's). day["deadline"] is the
    deadline fact from code (minutes or None)."""
    if not answers_result or answers_result.get("error"):
        return {"action": "error", "rule": "error", "reasons": [], "uses_budget": False,
                "label": (answers_result or {}).get("error") or "no result"}
    s = effective_settings(settings)
    answers = answers_result.get("answers") or {}
    r = _Reader(answers, s)
    if event["type"] == "ci_failure":
        return _decide_ci(event, r, s, day, answers)
    return _decide_message(event, r, s, day)


def replay_day(events: list[dict], results: dict, snapshot: dict, settings: dict | None,
               source: str = "jev") -> dict:
    """Routes the whole day in (time, id) order under the settings, from one answer source
    ("jev" or "baseline"), each with its own budget. Returns {event_id: decision}."""
    s = effective_settings(settings)
    out, left = {}, s["budget"]
    for event in sorted(events, key=lambda e: (e["time"], e["id"])):
        res = results.get(event["id"]) or {}
        day = {"budget_left": left, "snapshot": snapshot, "bar": rising_bar(s, left),
               "evening": event["time"] >= s["eveningStart"], "next_slot": res.get("next_free_slot"),
               "deadline": (res.get("facts") or {}).get("deadline_in_minutes")}
        d = decide(event, res.get(source), s, day)
        if d["uses_budget"]:
            left -= 1
        out[event["id"]] = {**d, "bar": day["bar"], "budget_left_after": left}
    return out
