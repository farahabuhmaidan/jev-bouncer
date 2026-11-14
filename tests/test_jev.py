import json
from pathlib import Path

import httpx

from pipeline.jev import ask_jev, normalize_answers
from pipeline.questions import CI_QUESTIONS, MESSAGE_QUESTIONS

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "jev_response.json").read_text())


def test_message_question_ids():
    assert set(MESSAGE_QUESTIONS) == {"needs_sanad", "time_sensitive", "wording_only_urgency", "family_matter",
                                      "blocks_release", "is_noise", "urgency"}


def test_ci_question_ids():
    assert set(CI_QUESTIONS) == {"failure_type", "cause_identifiable", "blocks_release"}


def test_questions_are_api_shaped():
    for q in {**MESSAGE_QUESTIONS, **CI_QUESTIONS}.values():
        assert q["type"] in {"noul", "choice", "score"} and q["instructions"]
        if q["type"] == "noul":
            assert set(q["criteria"]) == {"true", "false"}
    assert len(MESSAGE_QUESTIONS["urgency"]["criteria"]) == 5
    assert set(CI_QUESTIONS["failure_type"]["criteria"]) == {"flaky_test", "code_regression", "infra_problem", "config_or_lint"}


def test_parse_fixture():
    a = normalize_answers(FIXTURE["answers"])
    assert a["needs_sanad"] == 0.74
    assert a["failure_type"]["code_regression"] == 0.88
    assert a["urgency"] == {"score": 3.4, "probabilities": [0.02, 0.05, 0.1, 0.3, 0.53]}


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_ask_jev_sends_state_and_questions_and_parses():
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json=FIXTURE)

    out = ask_jev({"message": "hi"}, "message", client=_client(handler))
    assert seen["model"] == "typesafe/jev-1.14" and seen["state"] == {"message": "hi"}
    assert set(seen["questions"]) == set(MESSAGE_QUESTIONS)
    assert out["error"] is None and out["answers"]["needs_sanad"] == 0.74
    assert out["usage"]["cost"] == 1.8186e-05 and out["latency_ms"] >= 0 and out["request"]["state"] == {"message": "hi"}


def test_http_error_returns_error_not_answers():
    out = ask_jev({"message": "hi"}, "message", client=_client(lambda r: httpx.Response(500, text="boom")))
    assert out["answers"] == {} and "500" in out["error"]
