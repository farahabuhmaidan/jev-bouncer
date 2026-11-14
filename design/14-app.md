# 14 — The working app

Supersedes "Stage 2" in 01 and the layout in 07. Everything upstream stays: adapters (13), the state builder (02), the Jev questions (03), the policy rules (04), the LLM jobs (05), the data and labels (06) and the evaluation (08).

```
                 ┌──────────── React app (Vite) ─────────────┐
 browser ───────►│ Inbox · Why · Phone · Compose · Settings  │
 phone (wifi) ──►│ /phone: Sanad's phone only                │
                 └──────────────┬────────────────────────────┘
                                │ JSON over HTTP (poll 1 s)
                 ┌──────────────▼────────────────────────────┐
 curl / webhook ►│ FastAPI  server/app.py                     │
 (raw Slack, GH) │  adapters → state → Jev → policy → store   │
                 │  LLM auto-reply / CI explanation (thread)  │
                 └──────────────┬────────────────────────────┘
                                │ sqlite3
                       data/doorman.db (gitignored, rebuilt by `make seed`)
```

## Backend (`server/`)
- **One policy, in Python.** `server/policy.py` is the only routing code (ported from the first build's `web/policy.js`, same truth tables, same tests). `server/metrics.py` likewise. The browser never decides.
- **Seeded day.** `make seed` loads `data/events.json` + `data/snapshot.json` through `pipeline.load`, and the model outputs from `pipeline/cache/` via `pipeline.run.build_results(..., offline=True)`. No network.
- **Live events.** `POST /api/events` (unified event) or `POST /api/ingest/{source}` (raw payload → that source's adapter). The server builds the state, calls Jev synchronously, routes, stores, returns the decision. Auto-reply (people, decision batch) and CI explanation (Jev top failure_type = code_regression) are written by the LLM in a background thread and appear on the next poll. The LLM baseline is **not** called for live events (it exists to score the labelled set). Every event, seeded or live, also gets `facts.deadline_in_minutes` from `pipeline/state.deadline_minutes` (02), which policy row 5 reads.
- **Clock.** The server keeps the demo clock (`HH:MM`, starts 08:00). Seeded events become visible when the clock passes their time; a live event is stamped with the current clock. `POST /api/clock` sets it (play, jump, restart are client-driven calls to it).
- **Routing is recomputed, not stored.** Decisions = `replay_day(all events, results, snapshot, settings)` on every read: settings changes re-route the whole day instantly and the budget stays consistent.
- **Two answer sources, one policy.** `replay_day(..., source="jev")` routes Jev's answers; `source="baseline"` routes the baseline LLM's answers to the same questions (05), with its own budget. Metrics compare the two (08); live events have no baseline decision.

### API
| Method + path | Body / query | Returns |
|---|---|---|
| `GET /api/day` | | `{clock, settings, events:[{...event, result, decision, baseline_decision, feedback}] (time ≤ clock, newest first), phone:[ids], budget:{total, left}, evening}` |
| `GET /api/events/{id}` | | the event, its full result (state, facts, Jev answers, baseline answers, LLM text), decision and baseline_decision |
| `POST /api/events` | message `{sender \| sender_name, text, source?, channel?, time?, dry_run?}` or CI `{type:"ci_failure", branch, test_name, log_tail, commit_message?, time?, dry_run?}` | `201` + the event with result and decision (`200` for a dry run, nothing stored); `502` + stored ERROR event if Jev failed |
| `POST /api/ingest/{source}` | raw payload for a registered adapter | as above; `404` unknown source |
| `GET/PUT /api/settings` | settings object | the effective settings |
| `POST /api/clock` | `{time:"HH:MM"}` | `{clock}` |
| `POST /api/events/{id}/feedback` | `{kind:"ask", choice}` or `{kind:"urgent"}` | stored feedback |
| `GET /api/metrics` | | `{jev, llm}` each with critical_misses, precision, false_alarm_rate, cost_per_1k, p50, p95, accuracy, accuracy_excl_asks, holdout_accuracy, by_type, asks, errors; plus `n`, `settings_changed` (08), over labelled events only |
| `GET /api/digest` | | digest groups filtered to events currently batched |
| `GET /api/people` | | snapshot people (for Compose and Settings) |
| `GET /api/calendar` | | connection + reminders with each day's agenda (16) |
| `POST /api/events/{id}/reminder` | `{action: move\|keep\|remove\|add}` | the updated reminder (16) |
| `POST /api/reset` | | re-seed: deletes live events and feedback, clock 08:00 |

### SQLite schema (`server/db.py`)
- `events(id TEXT PK, time TEXT, origin TEXT /*seed|live*/, event JSON, label JSON NULL, holdout INT, demo_moment TEXT NULL)`
- `results(event_id TEXT PK, result JSON)`: state, facts, jev, baseline, auto_reply, ci_explanation, next_free_slot
- `kv(key TEXT PK, value JSON)`: `settings`, `clock`, `snapshot`
- `feedback(id INTEGER PK, event_id TEXT, kind TEXT, value TEXT, at TEXT)`

## Frontend (`frontend/`, Vite + React, no TypeScript)
- **Inbox** (left): events with action chip, urgency badge, label (who it was forwarded to / until when), auto-reply under batched people, "you chose …" after an ask. Live events get a "live" tag.
- **Why** (middle): rule fired, budget/bar, `deadline_in_minutes` (or "none"), Jev answer bars (bold = read by the rule), "baseline + same policy: action, row" (seeded events), label, CI explanation, the exact state JSON.
- **Phone** (right): interrupts and sender "truly urgent" re-routes; dimmed in evening. Also served alone at `/phone` (open on a real phone on the same wifi).
- **Compose** (top of inbox): sender dropdown (people), text box, Send. Shows a spinner, then the decision lands in the inbox and the Why panel opens on it.
- **Header**: clock, ▶ ⏸ ⏭ moment, 1x/10x, ↺ reset, budget dots, ⚙ settings, 👤 sender view, 📋 digest.
- **Test bench** (`/test`): a form for any notification (type, source, sender or an outside name, channel, time, text; or a CI failure's branch, test, commit and log). It shows the full response: decision, rule, Jev answers, state, auto-reply, raw JSON. **Dry run** by default (`dry_run: true` routes it against the real day, then removes it), so testing never pollutes the demo inbox.
- **Ask modal**: when a visible event's decision is "ask" and has no feedback, show it (only the question that was unsure: `needs_sanad`, else `time_sensitive`); the choice is POSTed as feedback and shown, never fed to metrics.
- **Metrics strip** (bottom): from `/api/metrics`, in the order critical misses, interrupt precision, cost per 1,000, p50 latency, then accuracy (all and excluding asks) and asks.
- Play is client-driven: a 1 s timer POSTs the next clock value (1 or 10 replay minutes per second).

## Live demo script (5 minutes)
1. ⏭ to 14:04 → the CEO's URGENT deck colour lands: batch + auto-reply. ⏭ → Rami's 0 JOD: interrupt, phone buzzes. Why panel: `wording_only_urgency 0.93` vs `blocks_release 0.93`.
2. ⏭ the CI trio: rerun silently · pinged DevOps (Lina) · interrupt + LLM explanation.
3. **Live:** type as Omar "can you jump on a call about the pricing bug before the investor demo? it's broken for discounted plans" → interrupt in ~1 s. Then as Layla "URGENT!!! pick a nicer font for slide 3" → batch + auto-reply appears a few seconds later.
4. ⏭ "got a sec?" → ask modal → click.
5. ⏭ evening: roadmap waits for morning, the school nurse gets through.
6. ⚙ drag the budget to 2 and "sure" to 0.8: the day re-routes, numbers update. 📋 digest.
Backup: the seeded day alone (no network) covers 1, 2, 4, 5, 6.

## Running
- `make install` (Python deps + `npm install` in `frontend/`), `make seed`, `make app` (builds the frontend, serves everything from FastAPI on `:8000`; `/slides/` too). `make dev` runs uvicorn `--reload` and Vite on `:5173` with a proxy to `/api`.
- Live events need `OPENROUTER_API_KEY` in `.env`; without it they are stored as ERROR and say so.
