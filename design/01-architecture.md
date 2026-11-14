# 01 — Architecture

## The idea
Jev connects to nothing. **Our code is the notification center.** Sources become one event shape, code adds context, Jev answers questions, and code decides.

```
Slack ─┐
Email ─┼─► adapters ─► unified event ─► context builder ─► Jev (judgments)
GitHub ┘  (slide only)  (events.json)    (state, no AI)        │
                                                                ▼
                                   policy in code (browser) ─► action
                                                                │
                              LLM writes text only where needed ┘
```

In the demo, `events.json` **is** the unified inbox. Sources plug in through adapters (see 13): Slack, Gmail and GitHub Actions adapters turn real-shaped payloads into unified events, and adding a source is one new file.

## Two stages

### Stage 1: `pipeline/run.py` (offline, run before the demo)
For every event in `data/events.json`:
1. Build the Jev state and the deadline fact (see 02). The fact is saved on the result and is not sent to either model.
2. Call Jev with the question set for its type (see 03). Save every answer and probability, the exact request payload and the latency.
3. Call the baseline LLM on the same state and the same questions (see 05). Save its answers, latency and tokens. Do not ask it for an action. The browser runs `decide` on these answers with the same policy it runs on Jev.
4. Where needed, call the LLM to write text: an auto-reply for **every message from a person** (not bots or CI), the CI explanation for regression events, and one digest at the end (see 05).

Writes `web/results.json`. Calls are cached in `pipeline/cache/` by event id plus a hash of the state and questions, so a rerun only calls for new or changed events (including reworded demo events). Calls run with a concurrency of 4. A failed call is retried once, then recorded as `{"error": "..."}`, never as an answer.

### `results.json` shape
```json
{
  "generated_at": "2026-11-14T14:10:00+03:00",
  "models": { "jev": "typesafe/jev-1.14", "llm": "anthropic/claude-sonnet-5.5" },
  "events": {
    "evt-031": {
      "state": { "...": "exact state sent to Jev (02)" },
      "jev": {
        "answers": { "needs_sanad": 0.91, "time_sensitive": 0.88, "failure_type": { "flaky_test": 0.05, "code_regression": 0.9 } },
        "latency_ms": 420, "usage": { "...": "as returned" }, "request": { "...": "exact payload" }, "error": null
      },
      "baseline": {
        "answers": { "needs_sanad": 0.42, "time_sensitive": 0.2, "wording_only_urgency": 0.8, "family_matter": 0.05, "blocks_release": 0.1, "is_noise": 0.08, "urgency": { "1": 0.1, "2": 0.7, "3": 0.15, "4": 0.04, "5": 0.01 } },
        "latency_ms": 1800, "tokens": { "in": 600, "out": 40 }, "error": null
      },
      "facts": { "deadline_in_minutes": null },
      "auto_reply": "Sanad's in a focus block until 16:00 ...",
      "ci_explanation": null
    }
  },
  "digest": { "groups": [ ] }
}
```
Noul answers are stored as the probability of yes. Choice answers are stored as the probability per option. The Score is stored as the probability per level.

### Stage 2: the app

> **Revised:** the static page below was the first build. The working app (FastAPI + SQLite + React, live events) is specified in [14-app.md](14-app.md); the policy now runs on the server.

#### First build: `web/index.html` (static page, no server)
Loads `events.json`, `snapshot.json` and `results.json`, then replays the day. **The routing policy (04) and the metrics (08) run in the browser in JS**, so changing a setting re-routes the whole day and updates the numbers instantly. There is exactly one implementation of the policy, and it lives in the browser.

Serve with `python -m http.server` from `web/`.

## Repo layout
```
data/        events.json, snapshot.json, ci_logs/*.txt, raw/<source>/*.json
pipeline/    run.py, load.py, questions.py (all Jev wording in one place),
             state.py, llm.py, adapters/ (base, slack, gmail, github_actions,
             google_calendar), cache/
web/         index.html, app.js, policy.js, metrics.js, style.css, results.json
design/      this spec
```

## Stack (decided)
- Python 3 for the pipeline, calling everything through **OpenRouter with one key**:
  - Jev: `POST https://openrouter.ai/api/alpha/decisions`, model `typesafe/jev-1.14` (pinned), body `{model, state, questions}` as in the TypeSafe docs. Plain `httpx`.
  - LLM: `POST https://openrouter.ai/api/v1/chat/completions`, model `anthropic/claude-sonnet-5.5`, with JSON-schema structured output where code reads the result.
- Page: plain HTML, CSS and JS with no build step. Builder's call: a single-file React via CDN is fine if faster for them.
- One key, from env var `OPENROUTER_API_KEY` (loaded from a gitignored `.env`). Keys never reach the page.

## Optional "live" button (only if time is left)
A tiny `pipeline/live.py` endpoint that sends one event to Jev and returns its answers. It can be cut first.
