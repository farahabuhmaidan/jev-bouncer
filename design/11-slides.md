# 11 — Presentation slides

A short HTML deck in `slides/index.html`, committed to the repo so it ships with the code and opens in any browser. No build step. Arrow keys move between slides. It is styled to match the demo page.

## Talk flow (about 5 minutes)
| # | Slide | Content |
|---|---|---|
| 1 | Title | Bouncer: a one-line pitch and the team |
| 2 | The problem | Hundreds of pings a day; wording sets urgency, so loud beats important. One example pair: the CEO's "URGENT!!!" deck colour vs Rami's quiet pricing bug |
| 3 | The idea | Both models answer the same judgments with probabilities; code decides; the LLM also writes. The truth table in miniature, including the deadline row |
| 4 | How it plugs in | Adapters → unified event → context builder → Jev → policy → LLM (diagram from 01). Real integrations are adapters; mocked today |
| 5 | **Live demo** | Switch to the page: loud vs quiet → CI trio → "got a sec?" ask → evening mode → drag the budget slider |
| 6 | The numbers | Jev vs baseline through the same policy, in this order: critical misses, interrupt precision, cost per 1,000, median and p95 latency, then accuracy (all and holdout). Date, models and n on the slide. Numbers are read from `results.json`. Losses shown |
| 7 | Privacy and limits | Personal sources are opt-in; mock data; small labelled set; demo events were reworded (link to `data/CHANGELOG.md`) |
| 8 | What's next | Real adapters, learning from "ask" answers, per-team policies; repo link |

## Rules
- Numbers on slide 6 are read from the running server's `/api/metrics`, never typed by hand.
- The same public-repo rules apply (10): no private links, fictional data only.
- Fallback if the live demo fails: slide 5 embeds the backup video.
