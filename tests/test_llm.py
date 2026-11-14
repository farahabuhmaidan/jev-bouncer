import json

import httpx

from pipeline import llm


def _reply(content, cost=0.001):
    return {"choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 600, "completion_tokens": 40, "cost": cost}}


def _client(content, seen=None, status=200):
    def handler(request):
        if seen is not None:
            seen.update(json.loads(request.content))
        return httpx.Response(status, json=_reply(content) if status == 200 else {"error": "x"})
    return httpx.Client(transport=httpx.MockTransport(handler))


STATE = {"now": "14:05, Sanad is in a focus block until 16:00", "sender": "Layla, CEO", "message": "URGENT!!! deck blue"}


MSG_ANSWERS = {"needs_sanad": 0.2, "time_sensitive": 0.1, "wording_only_urgency": 0.9, "family_matter": 0.0,
               "blocks_release": 0.05, "is_noise": 0.1,
               "urgency": {"level_1": 0.1, "level_2": 0.6, "level_3": 0.3, "level_4": 0.0, "level_5": 0.0}}


def test_baseline_judge_answers_in_jev_shape():
    out = llm.baseline_judge(STATE, "message", client=_client(json.dumps(MSG_ANSWERS)))
    a = out["answers"]
    assert out["error"] is None and a["needs_sanad"] == 0.2 and a["wording_only_urgency"] == 0.9
    assert a["urgency"]["probabilities"] == {"0": 0.1, "1": 0.6, "2": 0.3, "3": 0.0, "4": 0.0}
    assert abs(a["urgency"]["score"] - 1.2) < 1e-9
    assert out["tokens"] == {"in": 600, "out": 40} and out["cost"] == 0.001 and "action" not in out


def test_baseline_judge_asks_the_jev_questions_without_actions_or_settings():
    seen = {}
    llm.baseline_judge(STATE, "message", client=_client(json.dumps(MSG_ANSWERS), seen))
    prompt = json.dumps(seen["messages"])
    assert "Does Sanad need to handle `message` himself?" in prompt and "URGENT!!! deck blue" in prompt
    for word in ("interrupt", "delegate", "5 interrupts", "18:00", "deadline_in_minutes"):
        assert word not in prompt
    props = seen["response_format"]["json_schema"]["schema"]["properties"]
    assert set(props) == {"needs_sanad", "time_sensitive", "wording_only_urgency", "family_matter",
                          "blocks_release", "is_noise", "urgency"}


def test_baseline_judge_ci_choice_is_normalized():
    payload = {"failure_type": {"flaky_test": 1, "code_regression": 3, "infra_problem": 0, "config_or_lint": 0},
               "cause_identifiable": 0.9, "blocks_release": 0.8}
    a = llm.baseline_judge({"ci": {}}, "ci_failure", client=_client(json.dumps(payload)))["answers"]
    assert a["failure_type"] == {"flaky_test": 0.25, "code_regression": 0.75, "infra_problem": 0.0, "config_or_lint": 0.0}


def test_baseline_judge_out_of_range_is_error():
    out = llm.baseline_judge(STATE, "message", client=_client(json.dumps({**MSG_ANSWERS, "is_noise": 7})))
    assert out["answers"] == {} and out["error"]


def test_auto_reply_mentions_slot():
    seen = {}
    text = llm.auto_reply(STATE, "16:00", client=_client("Hi Layla, Sanad is heads-down until 16:00.", seen))
    assert "16:00" in json.dumps(seen["messages"]) and text.startswith("Hi Layla")


def test_ci_explain_parses():
    payload = {"likely_cause": "discount applied twice", "suspicious_lines": ["total = ..."], "suggested_fix": "remove second subtraction"}
    assert llm.ci_explain({"ci": {"log_tail": "x"}}, client=_client(json.dumps(payload))) == payload


def test_digest_parses():
    payload = {"groups": [{"title": "Leadership", "items": [{"event_id": "evt-014", "summary": "deck colour", "draft_reply": "Will do at 16:00"}]}]}
    assert llm.digest([{"id": "evt-014", "text": "deck"}], client=_client(json.dumps(payload))) == payload


def test_error_is_error():
    out = llm.baseline_judge(STATE, "message", client=_client("", status=500))
    assert out["answers"] == {} and "500" in out["error"]


def test_empty_content_is_error():
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": None}, "finish_reason": "length"}], "usage": {}})
    out = llm.baseline_judge(STATE, "message", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert out["answers"] == {} and "length" in out["error"]


def test_writing_jobs_use_low_reasoning_effort():
    seen = {}
    llm.auto_reply(STATE, "16:00", client=_client("ok", seen))
    assert seen["reasoning"] == {"effort": "low"}
