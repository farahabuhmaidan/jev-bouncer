"""One-off check that both models answer through OpenRouter. Sends mock data only.

Run: .venv/bin/python -m pipeline.probe
"""
import json
import os
import time

import httpx
from dotenv import load_dotenv

JEV_URL = "https://openrouter.ai/api/alpha/decisions"
LLM_URL = "https://openrouter.ai/api/v1/chat/completions"

STATE = {
    "now": "14:20, Sanad is in a focus block until 16:00",
    "sender": "Rami, junior dev on Sanad's Checkout team",
    "channel": "Slack DM",
    "message": "hey, is checkout supposed to show 0 JOD for some users?",
    "linked_items": ["CHK-88: checkout pricing, High priority, owned by Sanad, due today"],
}


def main() -> None:
    load_dotenv()
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    with httpx.Client(timeout=60, headers=headers) as client:
        t = time.perf_counter()
        jev = client.post(JEV_URL, json={
            "model": "typesafe/jev-1.14",
            "state": STATE,
            "questions": {
                "needs_sanad": {
                    "type": "noul",
                    "instructions": "Does Sanad need to handle `message` himself?",
                    "criteria": {
                        "true": "Only Sanad has the knowledge, ownership or authority to act, e.g. it is about a ticket he owns",
                        "false": "A teammate, a doc or anyone on the team could answer it",
                    },
                },
            },
        })
        print("JEV", jev.status_code, f"{(time.perf_counter() - t) * 1000:.0f}ms")
        print(json.dumps(jev.json(), indent=2)[:1500])

        t = time.perf_counter()
        llm = client.post(LLM_URL, json={
            "model": "anthropic/claude-sonnet-5.5",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "Reply with the single word: ready"}],
        })
        print("LLM", llm.status_code, f"{(time.perf_counter() - t) * 1000:.0f}ms")
        print(json.dumps(llm.json(), indent=2)[:1200])


if __name__ == "__main__":
    main()
