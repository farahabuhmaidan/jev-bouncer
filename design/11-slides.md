# 11 — Presentation slides

A short HTML deck in `slides/index.html`, committed to the repo so it ships with the code and opens in any browser. No build step. Arrow keys move between slides. It is styled to match the demo page.

## Talk flow (about 5 minutes)
Revised 2026-11-14: the deck tells the problem first, in plain human language; architecture gets one slide.

| # | Slide | Content |
|---|---|---|
| 1 | Title | Doorman: "The message that matters gets through. The loud one waits its turn." |
| 2 | Meet Sanad | Who he is, what his day holds (demo tomorrow, a fix to ship), 34 messages from everyone; fictional persona |
| 3 | Loud beats important | The CEO's "URGENT!!!" deck colour vs Rami's quiet 0 JOD bug, each with what it feels like vs what it is |
| 4 | Two bad options | Notifications on (everything gets through) vs do not disturb (nothing does, not even the school) |
| 5 | Doorman at the door | What it does, in outcomes: interrupt, hold + auto-reply, forward, ask, family, calendar reminder |
| 6 | How it decides | Jev answers the questions a good assistant would ask; plain rules decide; the LLM only writes; deadlines by code |
| 7 | Under the hood | Sources → event with context → Jev → rules → LLM text → the app and the phone |
| 8 | **Live demo** | loud vs quiet → CI trio → live message → "got a sec?" ask → evening mode → change a rule |
| 9 | The numbers | Jev vs the LLM through the same policy, read live from `/api/metrics`; losses shown |
| 10 | What we're honest about | Fictional data, small labelled set, changes logged, baseline prompt caveat, demo calendar |
| 11 | What's next | A real week for a real person, learning from answers, teams |

## Rules
- Numbers on the numbers slide (9) are read from the running server's `/api/metrics`, never typed by hand.
- The same public-repo rules apply (10): no private links, fictional data only.
- Fallback if the live demo fails: the demo slide (8) embeds the backup video.
