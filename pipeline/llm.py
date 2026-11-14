"""Every LLM prompt in one place (design/05-llm-jobs.md).

The LLM never routes in the product. It writes text after the policy has decided,
and, separately, acts as the LLM-only baseline Jev is measured against.
"""
from __future__ import annotations

import json
import os
import time

import httpx

LLM_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "anthropic/claude-sonnet-5.5"
ACTIONS = ["interrupt", "batch", "delegate", "drop"]

BASELINE_SYSTEM = """You are an attention assistant for Sanad, a product engineer at a startup.
For each incoming event, decide what to do with it. Choose exactly one action:
- interrupt: notify Sanad right now on his phone.
- batch: hold it for his next free slot or the end-of-day digest.
- delegate: forward it to a teammate, the support team or DevOps, who can handle it.
- drop: nothing to do (noise, automated notices, plain thanks); for a flaky CI test, rerun it silently.

Sanad's settings: 5 interrupts a day; family can always reach him when it can't wait (family that can wait is held); evening mode from 18:00, when work waits until
the morning unless it blocks the release or the investor demo.

Reply with JSON: the action, your confidence from 0 to 1 that it is the right action, and a one-line reason."""

BASELINE_SCHEMA = {
    "name": "route",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ACTIONS},
            "confidence": {"type": "number"},
            "reason": {"type": "string"},
        },
        "required": ["action", "confidence", "reason"],
        "additionalProperties": False,
    },
}

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


def baseline_route(state: dict, client: httpx.Client | None = None) -> dict:
    try:
        content, meta = _chat(BASELINE_SYSTEM, json.dumps(state, ensure_ascii=False, indent=1), BASELINE_SCHEMA,
                              max_tokens=3000, effort=None, client=client)
        out = json.loads(content)
        if out.get("action") not in ACTIONS:
            raise LLMError(f"action outside the four: {out.get('action')!r}")
        return {"action": out["action"], "confidence": out.get("confidence"), "reason": out.get("reason"),
                **meta, "error": None}
    except (LLMError, httpx.HTTPError, ValueError, KeyError) as exc:
        return {"action": None, "confidence": None, "reason": None, "error": f"{type(exc).__name__}: {exc}"}


def auto_reply(state: dict, next_slot: str, client: httpx.Client | None = None) -> str:
    user = json.dumps({"sender": state["sender"], "message": state.get("message"),
                       "sanad_will_look_at_it": next_slot}, ensure_ascii=False, indent=1)
    content, _ = _chat(AUTO_REPLY_SYSTEM, user, max_tokens=1500, client=client)
    return content.strip()


def ci_explain(state: dict, client: httpx.Client | None = None) -> dict:
    content, _ = _chat(CI_SYSTEM, json.dumps(state.get("ci", state), ensure_ascii=False, indent=1), CI_SCHEMA,
                       max_tokens=2500, client=client)
    return json.loads(content)


def digest(items: list[dict], client: httpx.Client | None = None) -> dict:
    content, _ = _chat(DIGEST_SYSTEM, json.dumps(items, ensure_ascii=False, indent=1), DIGEST_SCHEMA,
                       max_tokens=8000, client=client)
    return json.loads(content)
