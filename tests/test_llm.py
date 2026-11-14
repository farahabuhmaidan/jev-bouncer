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


def test_baseline_action_in_four():
    out = llm.baseline_route(STATE, client=_client(json.dumps({"action": "batch", "confidence": 0.8, "reason": "cosmetic"})))
    assert out["action"] == "batch" and out["confidence"] == 0.8 and out["error"] is None
    assert out["tokens"] == {"in": 600, "out": 40} and out["cost"] == 0.001


def test_baseline_prompt_has_default_settings_in_words_and_schema():
    seen = {}
    llm.baseline_route(STATE, client=_client(json.dumps({"action": "drop", "confidence": 0.5, "reason": "x"}), seen))
    prompt = json.dumps(seen["messages"])
    assert "5 interrupts a day" in prompt and "URGENT!!! deck blue" in prompt
    assert seen["model"] == "anthropic/claude-sonnet-5.5"
    assert seen["response_format"]["json_schema"]["schema"]["properties"]["action"]["enum"] == ["interrupt", "batch", "delegate", "drop"]


def test_baseline_bad_action_is_error():
    out = llm.baseline_route(STATE, client=_client(json.dumps({"action": "panic", "confidence": 1, "reason": ""})))
    assert out["action"] is None and out["error"]


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
    out = llm.baseline_route(STATE, client=_client("", status=500))
    assert out["action"] is None and "500" in out["error"]


def test_empty_content_is_error():
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": None}, "finish_reason": "length"}], "usage": {}})
    out = llm.baseline_route(STATE, client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert out["action"] is None and "length" in out["error"]


def test_writing_jobs_use_low_reasoning_effort():
    seen = {}
    llm.auto_reply(STATE, "16:00", client=_client("ok", seen))
    assert seen["reasoning"] == {"effort": "low"}
