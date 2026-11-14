"""Every LLM prompt in one place (design/05-llm-jobs.md).

The LLM never routes. It writes text after the policy has decided, and, separately,
answers the same questions as Jev so both answer sets can go through the same policy.
"""
from __future__ import annotations

import json
import os
import time

import httpx

from .questions import questions_for

LLM_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "anthropic/claude-sonnet-5.5"

BASELINE_SYSTEM = """You judge incoming events for Sanad, a product engineer at a startup.
You are shown the state of one event and a list of questions about it. Answer every question
from the state alone.
- A yes/no question: give the probability, from 0 to 1, that the answer is yes. The criteria say
  what yes and no mean.
- A choice question: give a probability for every option; they should add up to 1.
- A score question: give a probability for every level (level_1 is the first level listed); they
  should add up to 1.
Reply with JSON only."""


def _noul_text(q: dict) -> str:
    return f"{q['instructions']}\n  yes: {q['criteria']['true']}\n  no: {q['criteria']['false']}"


def baseline_prompt(state: dict, event_type: str) -> str:
    """The same state Jev sees and the same questions, written out in words. No actions, no settings."""
    lines = []
    for qid, q in questions_for(event_type).items():
        if q["type"] == "noul":
            lines.append(f"{qid} (yes/no): {_noul_text(q)}")
        elif q["type"] == "choice":
            opts = "\n".join(f"  {k}: {v}" for k, v in q["criteria"].items())
            lines.append(f"{qid} (choice): {q['instructions']}\n{opts}")
        else:
            levels = "\n".join(f"  level_{i + 1}: {c}" for i, c in enumerate(q["criteria"]))
            lines.append(f"{qid} (score): {q['instructions']}\n{levels}")
    return "State:\n" + json.dumps(state, ensure_ascii=False, indent=1) + "\n\nQuestions:\n" + "\n\n".join(lines)


def _probs(keys) -> dict:
    return {"type": "object", "properties": {k: {"type": "number"} for k in keys},
            "required": list(keys), "additionalProperties": False}


def baseline_schema(event_type: str) -> dict:
    props = {}
    for qid, q in questions_for(event_type).items():
        if q["type"] == "noul":
            props[qid] = {"type": "number"}
        elif q["type"] == "choice":
            props[qid] = _probs(list(q["criteria"]))
        else:
            props[qid] = _probs([f"level_{i + 1}" for i in range(len(q["criteria"]))])
    return {"name": "judgments", "strict": True,
            "schema": {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}}


def _p(v) -> float:
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 1:
        raise LLMError(f"probability out of range: {v!r}")
    return float(v)


def _dist(d: dict) -> dict:
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0 for v in d.values()):
        raise LLMError(f"bad distribution: {d!r}")
    total = sum(d.values())
    if total <= 0:
        raise LLMError(f"empty distribution: {d!r}")
    return {k: v / total for k, v in d.items()}


def normalize_judgments(raw: dict, event_type: str) -> dict:
    """The baseline's reply in Jev's answer shape: Noul -> p, Choice -> {option: p}, Score -> {score, probabilities}."""
    out = {}
    for qid, q in questions_for(event_type).items():
        if q["type"] == "noul":
            out[qid] = _p(raw[qid])
        elif q["type"] == "choice":
            out[qid] = _dist({k: raw[qid][k] for k in q["criteria"]})
        else:
            dist = _dist({str(i): raw[qid][f"level_{i + 1}"] for i in range(len(q["criteria"]))})
            out[qid] = {"score": sum(int(k) * v for k, v in dist.items()), "probabilities": dist}
    return out


AUTO_REPLY_SYSTEM = """Write a short auto-reply on Sanad's behalf to the sender of the message below.
Sanad is busy and will look at it at the time given. 1-2 friendly sentences, in the sender's register
(casual for a teammate, a bit more formal for leadership or people outside the company).
Say when Sanad will get back to them. Mention they can tap "truly urgent" if it can't wait.
Do not promise anything about the content. Reply with the message text only."""

CI_SYSTEM = """You are helping an engineer understand a failing CI run.
From the failing test, log tail and commit message, explain the likely cause, quote the suspicious lines
from the diff or log, and suggest a fix. Be concrete and brief."""

CI_SCHEMA = {
    "name": "ci_explanation",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "likely_cause": {"type": "string"},
            "suspicious_lines": {"type": "array", "items": {"type": "string"}},
            "suggested_fix": {"type": "string"},
        },
        "required": ["likely_cause", "suspicious_lines", "suggested_fix"],
        "additionalProperties": False,
    },
}

DIGEST_SYSTEM = """Write Sanad's end-of-day digest of the items that waited for him.
Group them by person or topic. For each item give a one-line summary, and a short draft reply if the item
needs a reply (null otherwise). Keep each event_id exactly as given."""

DIGEST_SCHEMA = {
    "name": "digest",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "groups": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "event_id": {"type": "string"},
                                    "summary": {"type": "string"},
                                    "draft_reply": {"type": ["string", "null"]},
                                },
                                "required": ["event_id", "summary", "draft_reply"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["title", "items"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["groups"],
        "additionalProperties": False,
    },
}


# Every request parameter, per job; also part of each job's cache key in pipeline/run.py.
BASELINE_PARAMS = {"max_tokens": 3000, "effort": None}
REPLY_PARAMS = {"max_tokens": 1500, "effort": "low"}
CI_PARAMS = {"max_tokens": 2500, "effort": "low"}
DIGEST_PARAMS = {"max_tokens": 8000, "effort": "low"}


class LLMError(RuntimeError):
    pass


def default_client() -> httpx.Client:
    return httpx.Client(timeout=120, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})


def _chat(system: str, user: str, schema: dict | None = None, max_tokens: int = 2000,
          effort: str | None = "low", client: httpx.Client | None = None) -> tuple[str, dict]:
    """Sonnet 5.5 always reasons first (it cannot be disabled), so max_tokens must leave room for it.
    Writing jobs use low effort; the baseline passes effort=None to run at the model's default."""
    body = {"model": LLM_MODEL, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if effort:
        body["reasoning"] = {"effort": effort}
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": schema}
    client = client or default_client()
    t0 = time.perf_counter()
    resp = client.post(LLM_URL, json=body)
    latency = round((time.perf_counter() - t0) * 1000)
    if resp.status_code != 200:
        raise LLMError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    choice = data["choices"][0]
    if not choice["message"].get("content"):
        raise LLMError(f"empty reply (finish_reason={choice.get('finish_reason')})")
    usage = data.get("usage", {})
    meta = {"latency_ms": latency, "tokens": {"in": usage.get("prompt_tokens"), "out": usage.get("completion_tokens")},
            "cost": usage.get("cost")}
    return choice["message"]["content"], meta


def baseline_judge(state: dict, event_type: str, client: httpx.Client | None = None) -> dict:
    """The LLM-only baseline: the same questions Jev answers, routed by the same policy (design/05)."""
    try:
        content, meta = _chat(BASELINE_SYSTEM, baseline_prompt(state, event_type), baseline_schema(event_type),
                              **BASELINE_PARAMS, client=client)
        return {"answers": normalize_judgments(json.loads(content), event_type), **meta, "error": None}
    except (LLMError, httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        return {"answers": {}, "error": f"{type(exc).__name__}: {exc}"}


def auto_reply(state: dict, next_slot: str, client: httpx.Client | None = None) -> str:
    user = json.dumps({"sender": state["sender"], "message": state.get("message"),
                       "sanad_will_look_at_it": next_slot}, ensure_ascii=False, indent=1)
    content, _ = _chat(AUTO_REPLY_SYSTEM, user, **REPLY_PARAMS, client=client)
    return content.strip()


def ci_explain(state: dict, client: httpx.Client | None = None) -> dict:
    content, _ = _chat(CI_SYSTEM, json.dumps(state.get("ci", state), ensure_ascii=False, indent=1), CI_SCHEMA,
                       **CI_PARAMS, client=client)
    return json.loads(content)


def digest(items: list[dict], client: httpx.Client | None = None) -> dict:
    content, _ = _chat(DIGEST_SYSTEM, json.dumps(items, ensure_ascii=False, indent=1), DIGEST_SCHEMA,
                       **DIGEST_PARAMS, client=client)
    return json.loads(content)
