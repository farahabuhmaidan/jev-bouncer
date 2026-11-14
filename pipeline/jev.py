"""Jev client: one request per event, all its questions together (design/03).

Calls Jev through OpenRouter. A failed call is returned as an error, never as
an answer: code must not read a failed call as "no".
"""
from __future__ import annotations

import os
import time

import httpx

from .questions import questions_for

JEV_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_MODEL = "typesafe/jev-1.14"


def normalize_answers(answers: dict) -> dict:
    """Noul → p(yes); Choice → {option: p}; Score → {score, probabilities}."""
    out = {}
    for qid, a in answers.items():
        if a["type"] == "noul":
            out[qid] = a["noul"]
        elif a["type"] == "choice":
            out[qid] = a["probabilities"]
        elif a["type"] == "score":
            out[qid] = {"score": a["score"], "probabilities": a["probabilities"]}
    return out


def default_client() -> httpx.Client:
    return httpx.Client(timeout=60, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})


def ask_jev(state: dict, event_type: str, client: httpx.Client | None = None) -> dict:
    request = {"model": JEV_MODEL, "state": state, "questions": questions_for(event_type)}
    client = client or default_client()
    t0 = time.perf_counter()
    try:
        resp = client.post(JEV_URL, json=request)
        latency = round((time.perf_counter() - t0) * 1000)
        if resp.status_code != 200:
            return {"answers": {}, "latency_ms": latency, "usage": {}, "request": request,
                    "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        body = resp.json()
        return {"answers": normalize_answers(body["answers"]), "latency_ms": latency,
                "usage": body.get("usage", {}), "model": body.get("model"), "request": request, "error": None}
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        return {"answers": {}, "latency_ms": round((time.perf_counter() - t0) * 1000), "usage": {},
                "request": request, "error": f"{type(exc).__name__}: {exc}"}
