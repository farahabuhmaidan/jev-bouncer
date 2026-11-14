# 05 — LLM jobs

Model: `anthropic/claude-sonnet-5.5` via OpenRouter, with structured output (a JSON schema) wherever the code reads the result. All runs happen in the pipeline, ahead of time.

## 1. Baseline judge (for the comparison)
- **Input:** the same state Jev saw (02). No action names. No Sanad settings. No `deadline_in_minutes`.
- **Output:** the same probabilities as `03`: for a message, `needs_sanad`, `time_sensitive`, `wording_only_urgency`, `family_matter`, `blocks_release`, `is_noise`, and the `urgency` score; for CI, `failure_type`, `cause_identifiable`, `blocks_release`.
- Record latency and input/output tokens per call.
- The action is not in this response. The browser computes it with `decide(event, answers, settings, dayState)` (04), the same function it uses for Jev. Moving a slider re-routes both columns.
- **Cut first if late:** an extra call where the model picks `interrupt` / `batch` / `delegate` / `drop` directly. That arm is not stored in the main `results.json` shape and does not appear on slide 6.

## 2. Auto-reply (every message from a person)
- **Written for:** every message event whose sender is a person (not a bot or CI), about 20–25 calls. The page shows a reply only while that message's current action is **batch**.
- **Input:** sender's name and relationship, the message, Sanad's next free slot at that time (computed in code from the calendar).
- **Output:** 1–2 friendly sentences with an ETA, in the sender's register (casual for a teammate, a bit more formal for the CEO). No promises about content.
- **UI:** shown under the event and in the sender view, with a "truly urgent" button. Pressing it during the demo plays a scripted re-route; it does not make a live call.

## 3. CI explanation (code_regression events)
- **Input:** test name, trimmed log tail, commit message and the diff snippet from the CI log file.
- **Output:** `{ likely_cause, suspicious_lines[], suggested_fix }`, shown on the phone when the interrupt arrives.

## 4. End-of-day digest (one call)
- **Input:** every event whose **label** is batch or delegate. The pipeline uses labels so the policy stays in one place (the browser).
- **Output:** grouped summary (by person or topic) with a draft reply for each item that needs one.
- Shown at the close of the replay. It is precomputed at default settings, which the UI states ("digest at default settings").

## Not in scope
Delegation drafts and RAG. A delegated event shows "forwarded to <teammate from People>" from code, with no LLM text.
