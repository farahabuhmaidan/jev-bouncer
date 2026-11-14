# 05 — LLM jobs

Model: `anthropic/claude-sonnet-5.5` via OpenRouter, with structured output (a JSON schema) wherever the code reads the result. All runs happen in the pipeline, ahead of time.

## 1. Baseline router (for the comparison)
- **Input:** the same state Jev saw (02), plus the four action names with one-line descriptions, plus Sanad's default settings in words ("5 interrupts a day; family can always reach him when it can't wait; evening mode from 18:00").
- **Output:** `{ action, confidence 0–1, one_line_reason }`.
- Record latency and input/output tokens per call.
- The baseline's actions are fixed; settings sliders don't change them.

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
