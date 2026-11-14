"""Routing policy (design/04). Ported from the first build's web/policy.test.js, same cases."""
import pytest

from server.policy import DEFAULTS, decide, effective_settings, replay_day

SNAPSHOT = {
    "devops_contact": "lina",
    "people": {
        "rami": {"name": "Rami", "lead": "yousef"}, "yousef": {"name": "Yousef", "lead": "sanad"},
        "noor": {"name": "Noor", "lead": "hana"}, "hana": {"name": "Hana", "lead": None},
        "lina": {"name": "Lina", "lead": None}, "layla": {"name": "Layla", "lead": None, "relationship": "leadership"},
        "omar": {"name": "Omar", "lead": None}, "maha": {"name": "Maha", "lead": None},
        "school": {"name": "Riverside School office", "lead": None}, "github-actions": {"name": "GitHub Actions", "is_bot": True},
    },
}
QUIET = {"needs_sanad": 0.9, "time_sensitive": 0.1, "wording_only_urgency": 0.1, "family_matter": 0.05,
         "blocks_release": 0.1, "is_noise": 0.05}


def msg(sender, time="14:10", id="e"):
    return {"id": id, "time": time, "type": "message", "sender": sender}


def ci(time="14:31", id="c"):
    return {"id": id, "time": time, "type": "ci_failure", "sender": "github-actions"}


def jev(**answers):
    return {"answers": {**QUIET, **answers}, "error": None}


def day(**over):
    return {"budget_left": 5, "bar": 0.7, "evening": False, "snapshot": SNAPSHOT, "next_slot": "16:00", **over}


def S(**over):
    return {**DEFAULTS, **over}


def test_row8_quiet_time_sensitive_interrupts_and_uses_budget():
    d = decide(msg("rami"), jev(time_sensitive=0.9), DEFAULTS, day())
    assert (d["action"], d["rule"], d["uses_budget"]) == ("interrupt", 8, True)
    assert any(r["q"] == "time_sensitive" for r in d["reasons"])


def test_row4_blocks_and_needs_interrupts_without_budget():
    d = decide(msg("rami"), jev(blocks_release=0.93), DEFAULTS, day(budget_left=0))
    assert (d["action"], d["rule"], d["uses_budget"]) == ("interrupt", 4, False)


def test_row5_wording_only_urgency_batched_until_next_slot():
    d = decide(msg("layla"), jev(time_sensitive=0.8, wording_only_urgency=0.93), DEFAULTS, day())
    assert (d["action"], d["rule"], d["label"]) == ("batch", 5, "until 16:00")


def test_row6_unsure_needs_sanad_asks():
    d = decide(msg("omar"), jev(needs_sanad=0.5), DEFAULTS, day())
    assert (d["action"], d["rule"]) == ("ask", 6)


def test_row7_delegates_to_lead():
    d = decide(msg("noor"), jev(needs_sanad=0.1), DEFAULTS, day())
    assert (d["action"], d["label"]) == ("delegate", "forwarded to Hana")


def test_row7_no_lead_or_sanad_lead_goes_to_team_channel():
    assert decide(msg("yousef"), jev(needs_sanad=0.1), DEFAULTS, day())["label"] == "forwarded to the team channel"


def test_row7_leadership_is_batched_not_delegated():
    d = decide(msg("layla"), jev(needs_sanad=0.1), DEFAULTS, day())
    assert (d["action"], d["rule"]) == ("batch", 7)


def test_row6_unsure_timing_does_not_ask_when_not_needed():
    assert decide(msg("noor"), jev(needs_sanad=0.1, time_sensitive=0.5), DEFAULTS, day())["action"] == "delegate"


def test_row6_unsure_timing_asks_when_needed():
    assert decide(msg("rami"), jev(time_sensitive=0.5), DEFAULTS, day())["action"] == "ask"


def test_row3_noise_dropped():
    assert decide(msg("noor"), jev(is_noise=0.9), DEFAULTS, day())["action"] == "drop"


def test_row9_otherwise_batch():
    d = decide(msg("rami"), jev(), DEFAULTS, day())
    assert (d["action"], d["rule"]) == ("batch", 9)


def test_row2_evening_batched_to_morning():
    d = decide(msg("omar", "19:30"), jev(time_sensitive=0.9), DEFAULTS, day(evening=True))
    assert (d["action"], d["rule"], d["label"]) == ("batch", 2, "until 09:00 tomorrow")


def test_row1_evening_school_interrupts():
    d = decide(msg("school", "18:40"), jev(family_matter=0.99, time_sensitive=0.83), DEFAULTS, day(evening=True))
    assert (d["action"], d["rule"], d["uses_budget"]) == ("interrupt", 1, False)


def test_row1_family_sender_unsure_timing_interrupts():
    d = decide(msg("maha"), jev(family_matter=0.5, time_sensitive=0.5), DEFAULTS, day())
    assert (d["action"], d["rule"]) == ("interrupt", 1)


def test_row1_family_that_can_wait_is_batched():
    d = decide(msg("maha"), jev(family_matter=0.98, time_sensitive=0.06, needs_sanad=0.5), DEFAULTS, day())
    assert (d["action"], d["rule"], d["label"]) == ("batch", 1, "until 16:00")


def test_row1_off_family_not_special():
    assert decide(msg("maha"), jev(family_matter=0.99), S(familyAlways=False), day())["rule"] != 1


def test_row2_skipped_when_blocks_release():
    d = decide(msg("rami", "19:00"), jev(blocks_release=0.95), DEFAULTS, day(evening=True))
    assert d["rule"] != 2 and d["action"] == "interrupt"


def ci_jev(kind, **extra):
    ft = {"flaky_test": 0.03, "infra_problem": 0.03, "config_or_lint": 0.03, "code_regression": 0.03, kind: 0.91}
    return {"answers": {"failure_type": ft, "cause_identifiable": 0.9, "blocks_release": 0.1, **extra}, "error": None}


def test_ci_flaky_drop_rerun_silently():
    d = decide(ci(), ci_jev("flaky_test"), DEFAULTS, day())
    assert (d["action"], d["label"]) == ("drop", "rerun silently")


def test_ci_flaky_silent_rerun_off_batch():
    assert decide(ci(), ci_jev("flaky_test"), S(silentRerun=False), day())["action"] == "batch"


def test_ci_infra_pings_devops():
    d = decide(ci(), ci_jev("infra_problem"), DEFAULTS, day())
    assert (d["action"], d["label"]) == ("delegate", "pinged DevOps (Lina)")


def test_ci_lint_batch():
    assert decide(ci(), ci_jev("config_or_lint"), DEFAULTS, day())["action"] == "batch"


def test_ci_regression_blocks_interrupts_even_in_evening_without_budget():
    d = decide(ci("19:00"), ci_jev("code_regression", blocks_release=0.91), DEFAULTS, day(evening=True, budget_left=0))
    assert (d["action"], d["uses_budget"]) == ("interrupt", False)


def test_ci_regression_otherwise_batch():
    assert decide(ci(), ci_jev("code_regression"), DEFAULTS, day())["action"] == "batch"


def test_ci_evening_regression_without_blocks_batch():
    assert decide(ci("19:00"), ci_jev("code_regression"), DEFAULTS, day(evening=True))["action"] == "batch"


def test_ci_unclear_cause():
    assert decide(ci(), ci_jev("code_regression", cause_identifiable=0.1, blocks_release=0.5), DEFAULTS, day())["action"] == "interrupt"
    assert decide(ci(), ci_jev("code_regression", cause_identifiable=0.1), DEFAULTS, day())["action"] == "batch"


def test_jev_error_is_error():
    assert decide(msg("rami"), {"answers": {}, "error": "HTTP 500"}, DEFAULTS, day())["action"] == "error"


def test_missing_result_is_error():
    assert decide(msg("rami"), None, DEFAULTS, day())["action"] == "error"


def test_clamp():
    s = effective_settings(S(yesAt=0.4, noAt=0.6))
    assert s["yesAt"] == 0.4 and s["noAt"] == pytest.approx(0.35)


def test_empty_evening_start_falls_back():
    assert effective_settings(S(eveningStart=""))["eveningStart"] == "18:00"
    assert effective_settings(S(eveningStart="25:99"))["eveningStart"] == "18:00"


def test_bad_people_lists_fall_back():
    s = effective_settings(S(family="x", vip=None, budget="lots", yesAt="high"))
    assert s["family"] == DEFAULTS["family"] and s["vip"] == [] and s["budget"] == 5 and s["yesAt"] == 0.7


def urgent(id, time, ts=0.99):
    return {"id": id, "time": time, "type": "message", "sender": "rami"}, {"jev": jev(time_sensitive=ts), "next_free_slot": "16:00"}


def replay(items, settings=DEFAULTS):
    events = [e for e, _ in items]
    return replay_day(events, {e["id"]: r for e, r in items}, SNAPSHOT, settings)


def test_sixth_interrupt_with_budget_5_batched():
    out = replay([urgent(f"u{i}", f"1{i}:00") for i in range(1, 7)], S(risingBar=False))
    assert [d["action"] for d in out.values()] == ["interrupt"] * 5 + ["batch"]


def test_rising_bar_with_one_left_is_085():
    items = [urgent(f"u{i}", f"1{i}:00") for i in range(1, 5)] + [urgent("u5", "15:00", ts=0.8)]
    out = replay(items)
    assert out["u5"]["action"] == "batch" and out["u5"]["bar"] == pytest.approx(0.85)


def test_vip_skips_budget():
    out = replay([urgent(f"u{i}", f"1{i}:00") for i in range(1, 7)], S(risingBar=False, vip=["rami"]))
    assert all(d["action"] == "interrupt" for d in out.values())


def test_evening_from_event_time_and_setting():
    assert replay([urgent("late", "18:30")], S(eveningStart="19:00"))["late"]["action"] == "interrupt"
    assert replay([urgent("late", "18:30")])["late"]["rule"] == 2


def test_same_minute_ordered_by_id():
    assert list(replay([urgent("b", "14:00"), urgent("a", "14:00")])) == ["a", "b"]
