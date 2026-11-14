# Bouncer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A replayable demo day where Jev judges each event, browser code routes it, the LLM writes text, and the page shows measured Jev vs LLM-only numbers. Plus slides and a public-ready README.

**Architecture:** An offline Python pipeline turns `data/` into `web/results.json` (Jev answers, baseline answers to the same questions, deadline facts, LLM texts). A static page loads it and runs one routing policy on both answer sets, plus the metrics, in the browser, so settings re-route both columns instantly. See `design/01-architecture.md`.

**Tech Stack:** Python 3.11+ (`httpx`, `pytest`, `python-dotenv`; every model call goes through OpenRouter), plain HTML/CSS/JS ES modules, Node 20+ only for `node --test` on the JS modules.

**Spec:** `design/README.md` and `design/01`–`11`. Read the spec file a task names before starting it.

## Global Constraints
- Public repo: no secrets (the only key is `OPENROUTER_API_KEY`, from a gitignored `.env`), fictional data only, no private links (`design/10-public-repo.md`).
- Jev never picks the action; all routing lives in `web/policy.js` only (`design/04-policy.md`).
- All Jev question wording lives in `pipeline/questions.py`; all LLM prompts in `pipeline/llm.py`.
- LLM model: `claude-sonnet-5-5`. Jev model id: whatever the TypeSafe models page names, recorded in `results.json.models.jev`.
- Defaults: `yesAt 0.7`, `noAt 0.3`, `interruptBar 0.7`, rising bar on, budget 5, evening start 18:00, `deadlineMinutes 120`, family-always-interrupts on, CI silent rerun on.
- A failed model call is an error, never an answer.
- Day runs 08:00–20:00; times are `"HH:MM"` strings.

## Review Focus
- An event whose `sender` is missing from `snapshot.people` → state says "Unknown sender (<key>)"; nothing crashes. Test in Task 3.
- `results.json` lacks an event, or has `jev.error` → ERROR chip, counted wrong, no crash. Tests in Tasks 6 and 7.
- Settings where `yesAt <= noAt` → policy clamps `noAt` to `yesAt - 0.05`. Test in Task 6.
- `localStorage` throws (private window) → defaults are used and the page still loads. Covered by the try/catch in Task 8, checked by hand in its verify step.
- Two events at the same minute → stable order by `id`. Test in Task 6.

---

### Task 1: Scaffold + probe both APIs (0:00–0:20)

**Files:** Create `requirements.txt`, `.env.example`, `Makefile`, `pipeline/__init__.py`, `pipeline/probe.py`, `pipeline/API_NOTES.md`

- [ ] **Step 1:** Read `https://docs.typesafe.ai/llms.txt`, then `/go/api.md`, `/go/primitives.md` and `/go/models.md` (append `.md`). Write `pipeline/API_NOTES.md` with: endpoint or SDK call, auth header, how one request carries state + several questions, exact type names for yes/no (Noul), Choice and Score, the response shape, model id, context and rate limits, and pricing if published (with its date and URL).
- [ ] **Step 2:** `requirements.txt`: `httpx`, `pytest`, `python-dotenv`. `.env.example` has `OPENROUTER_API_KEY=` with no value. Makefile targets: `install` (venv + pip), `test` (`pytest -q && node --test web/`), `pipeline` (`python -m pipeline.run`), `demo` (`python -m http.server 8000` from the repo root, then open `localhost:8000/web/`), `eval` (`python -m pipeline.run --eval-only`).
- [ ] **Step 3:** `pipeline/probe.py` sends one Jev request through OpenRouter (the state from `design/02` plus the `needs_sanad` Noul) and one Sonnet 5.5 chat completion, then prints both raw responses.
- [ ] **Step 4:** Run `make install && python -m pipeline.probe`. Expected: a Jev probability near yes for `needs_sanad` and a Sonnet reply. **Ask the user before the first live call** (it uses their keys and sends mock data only).
- [ ] **Step 5:** Commit: `chore: scaffold and API notes`.

### Task 2: Mock data + data checks (0:00–0:50, the user labels)

**Files:** Create `data/snapshot.json`, `data/events.json`, `data/ci_logs/{flaky,infra,regression}.txt` (+ 1–3 more), `data/CHANGELOG.md` (empty table), `tests/test_data.py`

**Interfaces:** Produces the shapes in `design/06-data.md` exactly.

- [ ] **Step 1: Write `tests/test_data.py`**: `test_every_event_labelled` (label.action ∈ {interrupt, batch, delegate, drop}), `test_senders_exist` (every sender is in snapshot.people), `test_demo_moments_present` (each of `loud-vs-quiet`, `ci-trio`, `unsure`, `evening` appears), `test_demo_events_not_holdout`, `test_holdout_count` (== 8), `test_budget_interrupts_at_most_5` (interrupt labels from 08:00 to 18:00 on messages that are not family and don't block the release ≤ 5), `test_ci_logs_exist`, `test_commitments_present` (snapshot has the CEO deck commitment), `test_evening_school_is_raw_gmail`, `test_customer_deadline_email_is_raw_gmail` (daytime, text contains "before 15:00", label interrupt).
- [ ] **Step 2:** Run `pytest tests/test_data.py`. Expected: FAIL (no files).
- [ ] **Step 3:** The agent drafts snapshot + ~35 events + CI logs per `design/06`. **The user sets or confirms every label.**
- [ ] **Step 4:** Run `pytest tests/test_data.py`. Expected: PASS.
- [ ] **Step 5:** Commit: `data: Sanad's day, labelled`.

### Task 2b: Source adapters (`design/13`)

**Files:** Create `pipeline/adapters/{__init__,base,slack,gmail,github_actions,google_calendar}.py`, `pipeline/load.py`, `data/raw/slack/*.json` (3), `data/raw/gmail/*.json` (2), `data/raw/github_actions/regression.json`, `data/raw/google_calendar/sanad-day.json`, `tests/test_adapters.py`, `tests/test_load.py`

**Interfaces:**
- Produces `ADAPTERS: dict[str, Adapter]`, `CONTEXT_ADAPTERS: dict[str, ContextAdapter]`, `register(cls)` (routes by type) and `resolve_sender(source: str, handle: str, people: dict) -> str`.
- Produces `load_snapshot(path: str) -> dict` and `load_events(path: str, snapshot: dict) -> list[dict]`. Tasks 3 and 9 use these instead of reading the JSON files directly.
- Calendar test cases: `test_calendar_focus_time_kind`, `test_calendar_pickup_is_personal`, `test_calendar_skips_cancelled_and_free`, `test_load_snapshot_expands_raw_calendar`.

- [ ] **Step 1: Tests:**
  - The contract test parametrized over `ADAPTERS` × fixtures (required fields, `HH:MM`, a known or `unknown:` sender, no network)
  - `test_slack_mention_resolved` (`"<@U07RAMI>"` → `"Rami"`)
  - `test_slack_dm_channel` (→ `"Slack DM"`)
  - `test_slack_bot_message_is_bot_sender`
  - `test_gmail_base64_body_decoded`
  - `test_gmail_quoted_history_cut`
  - `test_gmail_unsubscribe_hint`
  - `test_load_events_merges_label_from_raw_entry`
  - `test_unknown_raw_source_raises` (names the bad source)
- [ ] **Steps 2–5:** Confirm failing, implement, confirm passing. Convert at least 2 demo events to raw entries (Rami's Slack DM, the school email) so the demo really flows through adapters. Commit `feat: pluggable source adapters`.

### Task 3: State builder (`design/02`)

**Files:** Create `pipeline/state.py`, `tests/test_state.py`

**Interfaces:** Produces `build_state(event: dict, snapshot: dict) -> dict`, `deadline_minutes(event: dict, snapshot: dict) -> int | None`, and `next_free_slot(time: str, snapshot: dict, evening_start: str = "18:00") -> str`.

- [ ] **Step 1: Tests:**
  - `test_rami_state`: evt-031 yields keys `now, sanad, today, sender, channel, message, linked_items`; `linked_items[0]` starts with `"CHK-88"`; `"focus block until 16:00" in now`; no `commitment` key.
  - `test_ceo_state_includes_one_commitment` (the deck sentence; no second commitment)
  - `test_ci_state_has_ci_not_message`
  - `test_unknown_sender` → `"Unknown sender"`
  - `test_no_links_omits_linked_items` (the key is absent, not an empty list)
  - `test_no_budget_or_deadline_in_state` (`deadline_in_minutes` is absent from the Jev state)
  - `test_deadline_minutes_before_1500` (a 14:20 "before 15:00" message → 40)
  - `test_deadline_minutes_none_when_unparsed`
  - `test_next_free_slot`: `("14:20") == "16:00"`, free at `"12:00" → "12:30"`, `("19:10") == "09:00 tomorrow"`
- [ ] **Step 2:** Run and confirm they fail. **Step 3:** Implement (regexes `[A-Z]+-\d+`, `#\d+`; log tail = last error section, ≤ 40 lines). **Step 4:** Run and confirm they pass. **Step 5:** Commit: `feat: state builder`.

### Task 4: Jev questions + client (`design/03`)

**Files:** Create `pipeline/questions.py`, `pipeline/jev.py`, `tests/test_jev.py`, `tests/fixtures/jev_response.json` (saved from Task 1's probe)

**Interfaces:**
- Produces `MESSAGE_QUESTIONS`, `CI_QUESTIONS` (lists of dicts in the API's shape, with ids exactly as in `design/03`).
- Produces `ask_jev(state: dict, event_type: str) -> {"answers": dict, "latency_ms": int, "usage": dict, "request": dict, "error": str|None}`.
- Answers are normalized: Noul → float p(yes); Choice / Score → `{option: p}`.

- [ ] **Step 1: Tests:**
  - `test_message_question_ids == {needs_sanad, time_sensitive, wording_only_urgency, family_matter, blocks_release, is_noise, urgency}`
  - `test_ci_question_ids == {failure_type, cause_identifiable, blocks_release}`
  - `test_parse_fixture` (normalizes the saved response)
  - `test_http_error_returns_error_not_answers` (patch the transport to raise → `answers == {}`, `error` is set)
- [ ] **Steps 2–5:** Confirm failing, implement, confirm passing, commit `feat: jev questions and client`. Criteria text comes verbatim from `design/03`; the Score levels are written as situations.

### Task 5: LLM jobs (`design/05`)

**Files:** Create `pipeline/llm.py`, `tests/test_llm.py`

**Interfaces:** Produces:
- `baseline_judge(state, event_type) -> {answers, latency_ms, tokens:{in,out}, error}` with the same answer ids as `design/03`
- `auto_reply(state, next_slot: str) -> str`
- `ci_explain(state, diff: str) -> {likely_cause, suspicious_lines, suggested_fix}`
- `digest(items: list[dict]) -> {groups: [{title, items: [{event_id, summary, draft_reply|None}]}]}`

All use tool-use structured output, except `auto_reply`, which returns plain text. Do not implement a direct-action baseline unless the tasks above are done; that call is the first cut in `design/09`.

- [ ] **Step 1: Tests** with a fake Anthropic client:
  - `test_baseline_answers_match_question_ids`
  - `test_baseline_prompt_has_no_action_names_or_settings` (the prompt contains neither `"interrupt"` nor `"5 interrupts a day"`)
  - `test_auto_reply_mentions_slot`
  - `test_error_is_error`
- [ ] **Steps 2–5:** Confirm failing, implement, confirm passing, commit `feat: llm jobs`.

### Task 6: Routing policy in the browser (`design/04`)

**Files:** Create `web/policy.js`, `web/policy.test.js`

**Interfaces:**
- Produces `DEFAULTS` (Global Constraints values + `family: [...]` and `vip: []` sender keys).
- Produces `decide(event, answers, settings, day) -> {action, rule, reasons, usesBudget, label?}`. `action` ∈ interrupt | batch | delegate | drop | ask | error. `label` is a display string, e.g. "rerun silently", "pinged DevOps", "forwarded to Lina", "until 09:00 tomorrow", "deadline in 40 minutes". `reasons` includes `deadline_in_minutes` when rule 5 fires.
- Produces `replayDay(events, results, snapshot, settings) -> {jev: Map<eventId, decision>, baseline: Map<eventId, decision>}`. It sorts by (time, id), tracks the budget and evening **per answer source**, and computes the rising bar: `min(0.95, bar + 0.15 * (budget - left) / max(1, budget - 1))`. Deadline facts come from `results[id].facts`.

- [ ] **Step 1: Tests** (`node --test`), one per row of both truth tables:
  - Rami → interrupt row 9
  - CEO URGENT → batch row 6
  - Customer email, `deadline_in_minutes` 40, `no(is_noise)` → interrupt row 5, `usesBudget` false, reason contains "40"
  - Same email with `yes(is_noise)` → drop row 3
  - Evening message with `deadline_in_minutes` 30 and `no(is_noise)` → interrupt row 5, not batch row 2
  - Cofounder p(needs_sanad) = 0.5 → ask
  - Evening roadmap → batch row 2
  - Evening school → interrupt row 1
  - Evening blocks_release → not batched by row 2
  - Flaky → drop with label "rerun silently"
  - Infra → delegate "pinged DevOps"
  - Regression + blocks → interrupt
  - Evening CI regression without blocks → batch
  - The 6th time-sensitive interrupt with budget 5 → batch
  - VIP skips the budget
  - `jev.error` → error
  - A missing result → error
  - `yesAt <= noAt` is clamped
  - Same-minute events are ordered by id
- [ ] **Steps 2–5:** Confirm failing, implement, confirm passing, commit `feat: routing policy`.

### Task 7: Metrics (`design/08`)

**Files:** Create `web/metrics.js`, `web/metrics.test.js`

**Interfaces:** Produces `computeMetrics(events, jevDecisions, baselineDecisions, results, prices) -> {jev: Column, baseline: Column, settingsChanged: bool}`. `Column` is `{criticalMisses, interruptPrecision, falseAlarmRate, accuracy, accuracyExcludingAsks, holdoutAccuracy, byType:{message, ci}, asks, errors, p50, p95, costPer1k}`. "Rerun silently" maps to drop and "pinged DevOps" to delegate. `prices` is read from `web/prices.json` (written by the pipeline).

- [ ] **Step 1: Tests:**
  - A 4-event toy set gives exact critical-miss counts, interrupt precision, and accuracy
  - Ask counts as wrong in `accuracy`, is omitted from `accuracyExcludingAsks`, and is counted in `asks`
  - An error counts as wrong and is counted in `errors`
  - `costPer1k` is null when the Jev price is null
  - Both columns are present and computed from their own decision maps
- [ ] **Steps 2–5:** Confirm failing, implement, confirm passing, commit `feat: metrics`.

### Task 8: The page (`design/07`)

**Files:** Create `web/index.html`, `web/app.js`, `web/style.css`

**Interfaces:** Consumes Tasks 6–7. It fetches `../data/events.json`, `../data/snapshot.json`, `results.json` and `prices.json` (`make demo` serves the repo root).

- [ ] **Step 1:** Header with clock, ▶ ⏸ ⏭ moment, 1x/10x, budget dots, ⚙ and 👤.
- [ ] **Step 2:** Three columns: the feed (action chips, urgency badge, inline auto-reply on batched people), snapshot + why (state JSON, deadline fact, a bar per answer, rule fired, baseline action from the same policy), and the phone (interrupts only, CI explanation, dimmed in the evening). Below them, the metrics strip in the order critical misses, interrupt precision, cost, median latency, accuracy, with the "labels assume defaults" note.
- [ ] **Step 3:** Settings drawer (all `DEFAULTS` fields, including family/VIP tags per person). Any change calls `replayDay` and re-renders. Settings persist to localStorage inside try/catch.
- [ ] **Step 4:** The ASK modal (two candidate actions; the click is display-only), the sender view (scripted "truly urgent" re-route), and the digest overlay at 20:00.
- [ ] **Step 5: Verify by hand:** `make demo`, open `localhost:8000/web/`, jump through all 4 moments, and drag the budget to 2 to watch interrupts turn into batches. Then load the page in a private window and check that it still works. Take a screenshot to `docs/assets/screenshot.png`.
- [ ] **Step 6:** Commit: `feat: demo page`.

### Task 9: Pipeline run + tune (`design/01`, `06`)

**Files:** Create `pipeline/run.py`, `pipeline/prices.py`, `tests/test_run.py`, `pipeline/cache/`

**Interfaces:** Consumes Tasks 3–5. Produces `web/results.json` in the exact shape from `design/01`, plus `web/prices.json`.

- [ ] **Step 1: Tests** with fake `ask_jev` and LLM functions:
  - `test_results_shape`
  - `test_auto_reply_only_for_people` (none for bots or CI)
  - `test_ci_explain_only_for_regression_label`
  - `test_digest_uses_batch_delegate_labels`
  - `test_cache_key_changes_when_text_changes`
  - `test_error_recorded`
- [ ] **Step 2:** Implement with `concurrent.futures` (4 workers), one retry, and `--eval-only` (rebuilds from cache, no calls). Run the tests and confirm they pass.
- [ ] **Step 3:** **Ask the user, then run for real:** `make pipeline`. Open the page and check the 4 moments. If one misses, reword only that event, add a row to `data/CHANGELOG.md`, and rerun.
- [ ] **Step 4:** Commit `results.json`, the cache and the changelog: `data: real run`.

### Task 10: Slides (`design/11`)

**Files:** Create `slides/index.html` (+ `slides/style.css`)

- [ ] **Step 1:** 8 slides per `design/11`. Arrow-key navigation. Visual style matches `web/style.css`.
- [ ] **Step 2:** Slide 6 imports `../web/metrics.js` and `../web/results.json` and renders the numbers live from them, in the order in `design/11` (no hand-typed numbers). Slide 5 has a "Open demo" link and a `<video>` for `docs/assets/demo.mp4` if it exists.
- [ ] **Step 3: Verify:** `make demo`, open `localhost:8000/slides/`, click through. Commit: `feat: slides`.

### Task 11: Public README + repo files (`design/10`)

**Files:** Create `README.md`, `LICENSE` (MIT, the user as copyright holder), `AGENTS.md`

- [ ] **Step 1:** README sections 1–7 per `design/10`, with numbers copied from the metrics output plus a link to `web/results.json`, the date and n.
- [ ] **Step 2: Verify:** fresh clone into the scratchpad → `make demo` works with no `.env`; `make test` passes; `git grep -nE "sk-or-|OPENROUTER_API_KEY=.+"` finds nothing.
- [ ] **Step 3:** Commit and push: `docs: public README`.
