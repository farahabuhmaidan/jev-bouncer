# Bouncer — Design (hackathon cut)

Date: 2026-11-14 · Time box: 3 hours (hackathon) · Revised 14:10: from a replay page to a working app (see 14)

## What it is and why

Bouncer is a personal attention assistant. People in bridge roles get hundreds of pings a day from Slack, email and CI, and the wording decides what feels urgent, not the context. Loud messages win and important quiet ones get lost.

Bouncer puts every event through one Jev call that answers a few small judgments about it ("does Sanad need to handle this himself?", "is the urgency only in the wording?"). Plain code turns those answers into an action: **interrupt, batch, delegate or drop**. The LLM only writes text: auto-replies, the CI explanation and the digest. It also serves as the baseline Jev is measured against.

**Audience:** engineers at a hackathon. **What they must leave believing:** Jev routes attention better and more cheaply than an LLM alone, and the numbers prove it.

## Goals
- **A working app, driven live on stage.** A FastAPI backend with a small SQLite database owns events, Jev answers, decisions, settings and feedback. A React frontend shows Sanad's inbox, the "why" for every decision, his phone and the metrics.
- **Live routing.** Anyone can type a message as any person (or POST a raw Slack / GitHub payload through the adapters); the backend builds the state, calls Jev (~0.3 s), applies the policy and stores the decision. The LLM writes the auto-reply in the background.
- **The seeded day.** The same 33 labelled events are loaded from `data/` + the committed model outputs, so the measured Jev-vs-LLM comparison still holds and the demo works with no keys.
- Users manage their own settings (thresholds, budget, evening hours, people, rules); the server re-routes the whole day and the UI updates.
- Auto-replies to people whose messages get batched; Sanad's answers to "ask" and senders' "truly urgent" taps are stored.

## Non-goals
- Auth, multi-user, deploying anywhere but a laptop
- RAG / knowledge base, delegation drafts
- Editing Jev question wording from the UI

## Anti-goals (a failure even if it works)
- Jev picking the action itself. The decision must stay in visible code.
- Any number on the closing slide that wasn't measured.
- The demo **depending** on a live API call: the seeded day works offline; live calls are an addition, and a failed call shows ERROR, never a guess.

## Approaches considered
| | Approach | Trade-off | Verdict |
|---|---|---|---|
| A1 | Python script precomputes model output; a static page replays it | Nothing live can fail; but it isn't an app | First build (kept: the pipeline and its cache seed the app) |
| A2 | **FastAPI + SQLite backend, React (Vite) frontend; policy runs on the server; seeded day + live events** | A real app that reuses every tested piece; one more process to run | **Chosen** (2026-11-14, user: "it needs to actually work") |
| A3 | Node backend reusing `policy.js` | One policy language; but the pipeline, adapters and Jev client are Python | Rejected |

## Files
1. [01-architecture.md](01-architecture.md): pipeline, components, data flow
2. [02-context-builder.md](02-context-builder.md): the state sent to Jev
3. [03-jev-questions.md](03-jev-questions.md): the questions and their criteria
4. [04-policy.md](04-policy.md): truth table and user settings
5. [05-llm-jobs.md](05-llm-jobs.md): baseline, auto-reply, CI explanation, digest
6. [06-data.md](06-data.md): events, snapshot, CI logs, labels
7. [07-ui.md](07-ui.md): the screen
8. [08-evaluation.md](08-evaluation.md): metrics and how they're computed
9. [09-build-plan.md](09-build-plan.md): 3-hour clock, risks, open items
10. [10-public-repo.md](10-public-repo.md): layout, root README, rules for a public repo
11. [11-slides.md](11-slides.md): the presentation deck
12. [12-implementation-plan.md](12-implementation-plan.md): task-by-task build plan
13. [13-adapters.md](13-adapters.md): pluggable source adapters (Slack, Gmail, GitHub Actions, Google Calendar examples)
14. [14-app.md](14-app.md): **the working app**: backend API, SQLite schema, frontend screens, live demo script (supersedes the stage-2 page in 01 and the layout in 07)
15. [15-app-plan.md](15-app-plan.md): task-by-task build plan for the app
