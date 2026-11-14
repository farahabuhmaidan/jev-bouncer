# Bouncer — Design (hackathon cut)

Date: 2026-11-14 · Time box: 3 hours (hackathon)

## What it is and why

Bouncer is a personal attention assistant. People in bridge roles get hundreds of pings a day from Slack, email and CI, and the wording decides what feels urgent, not the context. Loud messages win and important quiet ones get lost.

Bouncer puts every event through one Jev call that answers a few small judgments about it ("does Sanad need to handle this himself?", "is the urgency only in the wording?"). Plain code turns those answers into an action: **interrupt, batch, delegate or drop**. The LLM only writes text: auto-replies, the CI explanation and the digest. It also serves as the baseline Jev is measured against.

**Audience:** engineers at a hackathon. **What they must leave believing:** Jev routes attention better and more cheaply than an LLM alone, and the numbers prove it.

## Goals
- A replayed day for one persona (Sanad) with 4 demo moments, plus a measured comparison of Jev against an LLM-only baseline.
- Users manage their own settings (thresholds, budget, evening hours, people, rules), and the day re-routes live in the browser.
- Auto-replies to people whose messages get batched.

## Non-goals
- Real Slack, email or GitHub integrations (a slide shows how adapters would work)
- RAG / knowledge base, delegation drafts, live sender escalation, auth, multi-user, persistence
- Editing Jev question wording from the UI (that would need fresh Jev calls)

## Anti-goals (a failure even if it works)
- Jev picking the action itself. The decision must stay in visible code.
- Any number on the closing slide that wasn't measured.
- The demo depending on a live API call.

## Approaches considered
| | Approach | Trade-off | Verdict |
|---|---|---|---|
| A1 | Python script precomputes all model output into `results.json`; a static page replays it, and the routing rules run in the browser | Nothing live can fail on stage; settings re-route instantly | **Chosen** |
| A2 | Live server calls Jev as each event replays, plus a separate eval script | Feels more real; two code paths, ~45 min more, stage risk | Rejected |
| B | Product-polish demo with no measured comparison | Weak with an engineering audience | Rejected (the user picked A) |

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
