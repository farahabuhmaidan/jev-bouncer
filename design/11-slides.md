# 11 — Presentation slides

A short HTML deck in `slides/index.html`, committed to the repo so it ships with the code and opens in any browser. No build step. Arrow keys move between slides. It is styled to match the demo page.

## Talk flow (about 5 minutes)
Revised 2026-11-14: the deck tells the problem first, in plain human language; architecture gets one slide.

| # | Slide | Content |
|---|---|---|
| 1 | Title | Doorman: "The message that matters gets through. The loud one waits its turn." |
| 2 | Attention, pulled left and right | Deep work needs unbroken hours; every app can tap you; most taps could have waited but said URGENT |
| 3 | Meet Sanad | Demo tomorrow; focus block 14:00–16:00; the timeline of what broke it (14:05 URGENT, 14:20 0 JOD, CI, "quick q", "got a sec?"); fictional persona |
| 4 | URGENT is a word, not a deadline | The CEO's "URGENT!!!" deck colour vs Rami's quiet 0 JOD bug: feels like vs is |
| 5 | Two bad options | Notifications on (the focus block lasts five minutes) vs do not disturb (not even the school) |
| 6 | Doorman at the door | What it does, in outcomes: interrupt, hold + auto-reply, forward, ask, family, calendar reminder |
| 7 | How it decides | Jev answers the questions a good assistant would ask; plain rules decide; the LLM only writes; deadlines by code |
| 8 | Under the hood | Sources → event with context → Jev → rules → LLM text → the app and the phone |
| 9 | **Live demo** | loud vs quiet → CI trio → live message → "got a sec?" ask → evening mode → change a rule |
| 10 | The numbers | Jev vs the LLM through the same policy, read live from `/api/metrics`; losses shown |
| 11 | What we're honest about | Fictional data, small labelled set, changes logged, baseline prompt caveat, demo calendar |
| 12 | What's next | A Doorman that learns you: full email and Teams access with a memory of what is urgent and how and when you reply (code still decides; lessons visible and undoable); a real week; whole teams |

## Rules
- Numbers on the numbers slide (10) are read from the running server's `/api/metrics`, never typed by hand.
- The same public-repo rules apply (10): no private links, fictional data only.
- Fallback if the live demo fails: the demo slide (9) embeds the backup video.
