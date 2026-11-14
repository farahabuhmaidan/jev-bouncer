# 03 — Jev questions

**Rule: Jev answers judgments; it never picks the action.** All wording lives in `pipeline/questions.py`. Each question gets its own question text plus criteria that describe yes and no as concrete situations. Every question for an event goes in **one** request.

Type names follow TypeSafe's docs: **Noul** means the probability that a statement is true, and **Choice** means one option out of several. Check the exact request syntax at https://docs.typesafe.ai/llms.txt (and `/go/api.md`, `/go/primitives.md`) in the first 20 minutes.

## Message events (Slack, email)
| id | Type | Question | Yes means | No means |
|---|---|---|---|---|
| `needs_sanad` | Noul | Does Sanad need to handle `message` himself? | Only Sanad has the knowledge, ownership or authority to act (e.g. it's about a ticket he owns) | A teammate, a doc or anyone on the team could answer it |
| `time_sensitive` | Noul | Will waiting until Sanad's next free slot cause harm? | Something breaks, a customer is affected, or a deadline today is missed if it waits | It would be just as useful answered tomorrow |
| `wording_only_urgency` | Noul | Does `message` sound urgent while nothing in it is actually time-critical? | Caps, "URGENT", "ASAP" or "!!!" about something that can wait (e.g. a deck colour change) | Either it doesn't sound urgent, or the urgency is real |
| `family_matter` | Noul | Is `message` about Sanad's family or personal life? | From or about family, school, a child or home | Work matter |
| `blocks_release` | Noul | Does `message` report something broken or missing that would stop today's release, the investor demo or a ticket due today from working? | A bug, outage or missing piece that stops one of these from working | Unrelated, or a cosmetic or optional change (e.g. a slide's colour) |
| `is_noise` | Noul | Is `message` informational with nothing for Sanad to do or read? | Newsletters, automated FYIs, reactions, "thanks!" | Has a question, request or information Sanad needs |
| `urgency` | Score 1–5 | How soon does `message` need a response? (display only, never routes) | Levels written as situations, 1 = "can wait days", 5 = "needs action within minutes" | |

Deadline proximity is not a Jev question. `state.py` computes `deadline_in_minutes` and the policy applies it (02, 04). `urgency` stays a badge.

## CI failure events
| id | Type | Question / options |
|---|---|---|
| `failure_type` | Choice | What caused this failure in `ci.log_tail`? Options, each described: `flaky_test` (passes on rerun, timing or ordering issue, no related code change), `code_regression` (a change in `ci.commit_message` broke behaviour the test checks), `infra_problem` (runner, network, registry or out-of-disk errors), `config_or_lint` (lint, formatting, type or config errors) |
| `cause_identifiable` | Noul | Does `ci.log_tail` show what failed? Paired with the Choice so code can tell when no option fits. |
| `blocks_release` | Noul | Is this failure on the investor demo branch or a release branch? |

## Rules for tuning
- Fix the state first, wording second. No criteria that name specific test events, and no thresholds fitted to single cases.
- Compare wording variants as separate questions in one request over the same state.
- Hold back about 8 events that are never used for tuning, and report on them too (08).
