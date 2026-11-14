# 08 — Evaluation

Only measured numbers go on screen. If Jev loses on a metric, show it anyway; the pitch then leans on the metrics it wins. The strip and slide 6 do not open with accuracy.

## Compared
- **Jev:** Jev's answers + `policy.js` at the current settings → action.
- **Baseline:** the baseline's answers to the same questions (05) + the same `policy.js` at the same settings → action.

Both columns move when a slider moves. Labels reflect **default settings**. The strip shows a small "settings changed: labels assume defaults" note whenever settings differ from the defaults. Slide 6 quotes the default-settings numbers.

## Metrics (computed in `web/metrics.js` from `results.json` + labels)
Shown in this order.

| Metric | Definition |
|---|---|
| Critical misses | Labelled `interrupt` events that got batch, drop or delegate. This is the missed urgent message. Lead with it. |
| Interrupt precision | Of the events the policy interrupted, the share whose label is `interrupt`. False-alarm rate = 1 − this number. Report both. |
| Cost per 1,000 events | **Routing only**: one Jev request per event vs one baseline LLM call per event (the text-writing calls are the same on both sides, so they're left out). Measured: the mean of each call's `usage.cost` as returned by OpenRouter, times 1,000 (Jev 1.14: $0.042 per million input tokens, output free; Sonnet 5.5: $2 / $10 per million input / output tokens, both checked 2026-11-14). |
| Latency | Median and p95 per call, measured in the pipeline from the laptop |
| Accuracy | Share of events whose action matches the label, covering messages and CI. Shown overall, on holdout only, and per type (message / CI). An "ask" counts as wrong here. For CI events, "rerun silently" counts as drop and "pinged DevOps" as delegate. |
| Accuracy excluding asks | The same accuracy after events whose action is "ask" are removed from the numerator and the denominator. |
| Asks | How many events the policy sent to Sanad as "ask", counted separately for each answer source. |
| Calibration (stretch) | For `needs_sanad`, bucket p into 0.1 bins and compare against the labels. Only if time is left. |

Clicks in the "ask Sanad" modal never change the metrics. "Ask" is not a label. It counts as wrong in accuracy, is excluded in the second accuracy, and is reported as its own count.

## Before the demo
Run the pipeline on the full set once, commit `results.json`, and rehearse from it. No live run is needed during the talk.
