# 08 — Evaluation

Only measured numbers go on screen. If Jev loses on a metric, show it anyway; the pitch then leans on the metrics it wins.

## Compared
- **Jev:** Jev's answers + `policy.js` at the current settings → action.
- **LLM-only:** the baseline router's action (05). It's fixed and doesn't move with settings.

Labels reflect **default settings**. The strip shows a small "settings changed: labels assume defaults" note whenever settings differ from the defaults.

## Metrics (computed in `web/metrics.js` from `results.json` + labels)
| Metric | Definition |
|---|---|
| Accuracy | Share of events whose action matches the label, covering messages and CI. Shown overall, on holdout only, and per type (message / CI). An "ask" counts as wrong for accuracy. For CI events, "rerun silently" counts as drop and "pinged DevOps" as delegate. |
| Critical misses | Labelled `interrupt` events that got batch, drop or delegate. This is the costly error. |
| Asks | How many events Jev's policy sent to Sanad as "ask" (the LLM has none) |
| Latency | Median and p95 per call, measured in the pipeline from the laptop |
| Cost per 1,000 events | **Routing only**: one Jev request per event vs one baseline LLM call per event (the text-writing calls are the same on both sides, so they're left out). Use TypeSafe's published pricing, per request or per question, whichever it charges, and Anthropic's per-token prices, entered by hand with a date in `pipeline/prices.py`. If no public Jev price can be found, show calls and tokens instead of dollars and say so. |
| Calibration (stretch) | For `needs_sanad`, bucket p into 0.1 bins and compare against the labels. Only if time is left. |

Clicks in the "ask Sanad" modal never change the metrics. "Ask" is not a label; it counts as wrong for accuracy and is reported separately as the ask count.

## Before the demo
Run the pipeline on the full set once, commit `results.json`, and rehearse from it. No live run is needed during the talk.
