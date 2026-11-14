# Bouncer App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Bouncer from a replay page into a working app: FastAPI + SQLite backend that routes seeded and live events, and a React frontend driven live in the demo.

**Architecture:** The server owns events, model outputs, settings and feedback in SQLite, and recomputes decisions with the one Python policy on every read. Live events go adapters → state → Jev → policy synchronously; the LLM writes text in a background thread. React polls `/api/day` every second.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, sqlite3 (stdlib), httpx; React 18 + Vite 5 (plain JS); pytest + FastAPI TestClient.

**Spec:** `design/14-app.md` (with 02–06, 08, 13 unchanged and 04 for the rules).

## Global Constraints
- Policy defaults: yesAt 0.7, noAt 0.3, interruptBar 0.7, risingBar on, budget 5, eveningStart "18:00", familyAlways on, silentRerun on, family ["maha","school"], vip [].
- Rising bar `min(0.95, bar + 0.15*(budget-left)/max(1, budget-1))`; clamp `noAt = yesAt - 0.05` when `yesAt <= noAt`; an empty or malformed `eveningStart` falls back to "18:00".
- A failed Jev call is stored and shown as ERROR, never routed, never a "no".
- Labels are read only by metrics. LLM baseline is not called for live events.
- Public repo: no secrets, fictional data only; `data/bouncer.db` is gitignored.
- One policy implementation (Python). `web/` static page and JS policy are removed once the React app replaces them.
- Commits without Claude attribution.

## Review Focus
1. Empty or bad `eveningStart` / non-list `family`/`vip` in PUT settings → falls back to defaults, never sends the whole day to evening (test in Task 1, Task 3).
2. Jev down or no key during a live POST → event stored with ERROR, 502, UI shows ERROR chip (test in Task 2).
3. Live event at a clock time equal to a seeded event → ordering by (time, id) stays stable; live ids `live-<n>` (test in Task 2).
4. Unknown sender name / empty text in Compose → 422, nothing stored (test in Task 3).
5. Cache keys include model, schema, max_tokens and effort for every LLM call (test in Task 2).

---

### Task 1: Policy and metrics in Python

**Files:** Create `server/__init__.py`, `server/policy.py`, `server/metrics.py`, `tests/test_policy.py`, `tests/test_metrics.py`.

**Interfaces:**
- Produces `DEFAULTS: dict`, `effective_settings(s) -> dict`, `decide(event, jev, settings, day) -> dict{action, rule, reasons:[{q,p,value?}], uses_budget, label?}`, `replay_day(events, results, snapshot, settings) -> dict[id, decision + {bar, budget_left_after}]` (insertion order = (time, id)).
- Produces `compute_metrics(events, decisions, results, settings=None) -> {jev:{accuracy, holdout_accuracy, by_type:{message,ci}, critical_misses, asks, errors, p50, p95, cost_per_1k}, llm:{same minus asks}, settings_changed}`; only events with `label` count.

- [ ] **Step 1:** Port every test in `web/policy.test.js` (41 incl. metrics) to pytest with the same names (snake_case) and values. Add `test_empty_evening_start_falls_back` (eveningStart "" → event at 14:10 not evening) and `test_bad_people_lists_fall_back` (family "x" → treated as default list).
- [ ] **Step 2:** `.venv/bin/python -m pytest tests/test_policy.py tests/test_metrics.py` → FAIL (module missing).
- [ ] **Step 3:** Implement by porting `web/policy.js` and `web/metrics.js` line for line (same row order, labels and CI rules); validate settings in `effective_settings`.
- [ ] **Step 4:** Tests pass; also assert on the real `web/results.json` that `replay_day` gives the same actions as `node web/print-metrics.mjs` (Jev 64%, LLM 76%) in `test_metrics_match_first_build`.
- [ ] **Step 5:** Commit `feat(server): policy and metrics in Python`.

### Task 2: Store, seed and live processing

**Files:** Create `server/db.py`, `server/live.py`, `tests/test_db.py`, `tests/test_live.py`. Modify `pipeline/run.py` (cache keys), `requirements.txt` (fastapi, uvicorn), `.gitignore` (`data/bouncer.db`).

**Interfaces:**
- `Store(path)`: `seed(snapshot, events, results)`, `all_events() -> list`, `results() -> dict`, `add_event(event, result, origin="live")`, `set_result(id, patch)`, `get/put(key, value)`, `add_feedback(id, kind, value)`, `feedback() -> dict[id, list]`, `reset_live()`.
- `seed_store(store)`: loads data via `pipeline.load` + `build_results(..., offline=True)`.
- `process_event(store, event, ask=ask_jev, write=llm_writer) -> (event, result, decision)`: stamps `time` = store clock if missing, id `live-<n>`, builds state, calls Jev (one retry), stores; on error stores result with `jev.error`. Starts `write(store, event, result)` in a thread for auto-reply / CI explanation.

- [ ] **Step 1: Tests:** `test_seed_loads_33_events_with_results`, `test_reset_live_keeps_seed`, `test_live_event_gets_id_time_and_decision` (fake ask → interrupt via row 4), `test_live_jev_error_is_stored_as_error`, `test_live_same_minute_orders_by_id`, `test_auto_reply_written_for_batched_person` (fake writer, join thread), `test_cache_keys_cover_model_schema_tokens_effort` (changing `BASELINE_SCHEMA` or `LLM_MODEL` changes the key).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (sqlite3, JSON columns, `check_same_thread=False` + a lock). Cache keys: add `llm.LLM_MODEL`, the schema, `max_tokens`, `effort` to every LLM key in `run.py`; run `make eval` and confirm the README numbers are unchanged (the keys change, so run `make pipeline` once only if the user approves the ~$0.15 rerun; otherwise migrate keys with a one-off rename script and say so in the ledger).
- [ ] **Step 4:** Tests pass. **Step 5:** Commit `feat(server): sqlite store, seed and live processing`.

### Task 3: API

**Files:** Create `server/app.py`, `tests/test_api.py`. Modify `Makefile` (`seed`, `app`, `dev`, `install` adds npm).

**Interfaces:** routes exactly as in `design/14-app.md` § API. `create_app(store, ask=..., write=...) -> FastAPI` for tests; module-level `app` uses `data/bouncer.db` (seeds on first start if empty), serves `frontend/dist` at `/` (SPA fallback for `/phone`) and `slides/` at `/slides`.

- [ ] **Step 1: Tests** (TestClient, fakes): `test_day_hides_future_events` (clock 09:00 → only events ≤ 09:00), `test_settings_put_reroutes` (budget 1 → fewer interrupts in `/api/day` at 20:00), `test_settings_put_bad_values_fall_back`, `test_post_event_live` (201, decision present), `test_post_event_unknown_sender_422`, `test_post_event_empty_text_422`, `test_post_event_jev_down_502_and_stored`, `test_ingest_slack_raw_uses_adapter`, `test_ingest_unknown_source_404`, `test_feedback_ask_never_changes_metrics`, `test_metrics_shape`, `test_digest_only_batched`, `test_reset`.
- [ ] **Step 2–4:** FAIL → implement → pass. **Step 5:** Commit `feat(server): API`.

### Task 4: Frontend

**Files:** Create `frontend/` (Vite React): `package.json`, `vite.config.js` (proxy `/api` → `:8000`), `index.html`, `src/main.jsx`, `src/App.jsx`, `src/api.js`, `src/components/{Header,Inbox,Compose,Why,Phone,Settings,AskModal,Digest,Metrics}.jsx`, `src/style.css` (port `web/style.css` tokens). Delete `web/` (after Task 6 slides switch).

**Interfaces:** consumes the API only. `api.js` exports `getDay()`, `getEvent(id)`, `postEvent({sender,text})`, `putSettings(s)`, `setClock(t)`, `feedback(id, body)`, `getMetrics()`, `getDigest()`, `getPeople()`, `reset()`.

- [ ] **Step 1:** Scaffold, `npm install`, `npm run build` succeeds.
- [ ] **Step 2:** Screens per `design/14-app.md` § Frontend; `/phone` route renders Phone alone.
- [ ] **Step 3: Verify by hand:** `make app`, walk the live demo script steps 1–6, then load `/phone` in a second window. Screenshot to `docs/assets/screenshot.png`.
- [ ] **Step 4:** Commit `feat: React frontend`.

### Task 5: Slides, README, cleanup

**Files:** Modify `slides/slides.js` (numbers from `/api/metrics`), `slides/index.html` (slide 4 diagram, slide 5 live demo steps), `README.md` (quickstart `make install && make seed && make app`, architecture, live demo), `AGENTS.md`, `design/10-public-repo.md` layout. Remove `web/` and the JS tests from `make test`.

- [ ] **Step 1:** `make test` green; fresh clone → `make install seed app` works with no `.env` (live posts show ERROR with a clear message).
- [ ] **Step 2:** Commit `docs: app README and slides`; push `build`.

### Task 6: Same-policy comparison and the deadline row (teammate design update, commit a41d645)

**Files:** Modify `pipeline/state.py`, `pipeline/llm.py`, `pipeline/run.py`, `server/policy.py`, `server/metrics.py`, `server/print_metrics.py`, `server/live.py`, `server/app.py`, `frontend/src/components/{Why,Metrics,Settings}.jsx`, `slides/`, `data/{snapshot,events}.json`, `data/raw/gmail/customer-deadline.json`, `data/CHANGELOG.md`, README. Spec: 02, 04, 05, 06, 07, 08 as updated.

**Interfaces:**
- `deadline_minutes(event, snapshot) -> int | None` ("by/before HH:MM", "today" and a linked ticket due today end at 18:00; nearest future one). Stored as `result.facts.deadline_in_minutes`, never in the state.
- `snapshot.commitments[{who, what, when, about?}]` → `state.commitment` when `who` is the sender and the text mentions an `about` keyword (or a linked ticket matches).
- `llm.baseline_judge(state, event_type) -> {answers (Jev shape), latency_ms, tokens, cost, error}`; `baseline_route` removed.
- `decide(event, answers_result, settings, day)` reads `day["deadline"]`; row 5 = deadline < `deadlineMinutes` (15–480, default 120) and `no(is_noise)` → interrupt, no budget, reason `{q: "deadline_in_minutes", value}`; row 2 steps aside for it; rows 6–10 renumbered.
- `replay_day(..., source="jev"|"baseline")`; `compute_metrics(events, decisions, results, settings, baseline=decisions)` adds precision, false_alarm_rate, accuracy_excl_asks, asks for both columns.
- `/api/day` and `/api/events/{id}` add `baseline_decision` (None for live).

- [x] **Step 1:** Tests first: `test_state` (deadline, commitment, customer sender), `test_data` (evt-034), `test_llm` (judge shape, prompt has no actions/settings, normalisation, out-of-range error), `test_run` (facts, judge in cache key), `test_policy` (row 5 cases, renumbering, source), `test_metrics` (precision, excl. asks, baseline errors), `test_live`/`test_api` (facts, baseline_decision, deadlineMinutes). Watched each fail.
- [x] **Step 2:** Implement; UI: Why shows deadline and "baseline + same policy"; metrics strip and slide 6 in the new order; settings stepper.
- [x] **Step 3:** `make pipeline` (≈ $0.20: 34 baseline calls, Jev + reply for evt-014 and evt-034, digest), then `make eval`, update README numbers, `make test` green, commit.
