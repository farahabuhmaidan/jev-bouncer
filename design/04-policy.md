# 04 — Decision policy and user settings

Lives in `web/policy.js` as a pure function: `decide(event, jevAnswers, settings, dayState) → { action, rule, reasons }`. `rule` names the row that fired, and `reasons` lists the Jev answers it read. The "why was I interrupted?" view shows exactly these, with no generated text.

Notation: `yes(q)` means p ≥ `settings.yesAt`, `no(q)` means p ≤ `settings.noAt`, and anything in between is **unsure**.

## Message truth table (first matching row wins)
| # | Condition | Action | Uses budget |
|---|---|---|---|
| 1 | `yes(family_matter)` and rule "family always interrupts" on, or sender marked family | interrupt | no |
| 2 | Evening mode active and not `yes(family_matter)` and not `yes(blocks_release)` | batch (to morning) | n/a |
| 3 | `yes(is_noise)` | drop | n/a |
| 4 | `yes(blocks_release)` and `yes(needs_sanad)` | interrupt | no |
| 5 | `yes(wording_only_urgency)` and not `yes(blocks_release)` | batch (+ auto-reply) | n/a |
| 6 | `needs_sanad` or `time_sensitive` is unsure | **ask Sanad** | n/a |
| 7 | `no(needs_sanad)` | delegate | n/a |
| 8 | `yes(time_sensitive)` and budget left ≥ 1 and `p(time_sensitive)` ≥ current interrupt bar | interrupt | yes |
| 9 | otherwise | batch | n/a |

Row 5 comes before the delegate and ask rows on purpose: loud-but-not-time-critical messages (the CEO's deck colour) are batched with an auto-reply, not forwarded or asked about. A message from a manager or leadership gets batched, not delegated, because the sender asked Sanad directly.

Senders marked **VIP** skip the budget check in row 8.

**Unsure answers on other questions.** Only `needs_sanad` and `time_sensitive` trigger "ask". For every other question, an unsure answer counts as **not yes**, and the row is skipped.

**Delegate target.** Code picks who receives it and writes "forwarded to <name>" (no LLM): the sender's team lead from `snapshot.people`, or the DevOps contact for infra. If neither exists, it says "forwarded to the team channel".

**Next free slot** (used by auto-replies and shown on batched events), computed in code from the calendar: the end of the current meeting or focus block; if Sanad is free, now + 30 min; in evening mode, 09:00 the next morning.

## CI truth table
| Condition | Action |
|---|---|
| `no(cause_identifiable)` | interrupt with "unclear failure" (or batch if `no(blocks_release)`) |
| top `failure_type` = flaky_test and rule "silent rerun" on | drop, marked "rerun silently" |
| infra_problem | delegate, marked "pinged DevOps" |
| config_or_lint | batch |
| code_regression and `yes(blocks_release)` | interrupt + show the LLM explanation |
| code_regression otherwise | batch + LLM explanation in the digest |

Evening mode applies to CI too: in the evening every CI row becomes batch except a code_regression with `yes(blocks_release)`, which still interrupts. CI interrupts never use the budget.

## When a Jev call failed
An event whose Jev call errored shows an **ERROR** chip and is never routed. It is not treated as a "no". It counts as wrong in accuracy and is listed separately in the metrics strip.

## Day state (computed as the replay runs)
- Budget left = budget − interrupts that used budget so far today.
- **Interrupt bar** = `settings.interruptBar` when the rising bar is off. When it's on, it climbs linearly from `interruptBar` (full budget) to `interruptBar + 0.15` (1 left), capped at 0.95.
- Evening mode is active when the event time falls in `[eveningStart, 24:00)`.

## "Ask Sanad" during replay
Replay pauses and a modal shows the two candidate actions with the unsure probabilities. The click sets that event's action on screen and is listed as a session note. It does not change Jev's answers, and **it never reaches the metrics**: metrics always use the policy's own output, where an ask stays an ask (08).

## Settings panel (defaults)
| Setting | Control | Default |
|---|---|---|
| `yesAt` / `noAt` (the "sure" band) | dual slider | 0.7 / 0.3 |
| `interruptBar` | slider 0.5–0.95 | 0.7 |
| Rising bar | toggle | on |
| Daily budget | stepper 1–10 | 5 |
| Evening start | time | 18:00 |
| People: family / VIP | tag per contact | family = Sanad's partner and the school; VIP = none |
| Rules: family always interrupts, CI silent rerun | toggles | on |

Any change re-runs `decide` over the whole day from 00:00 and re-renders the feed, phone and metrics. Settings are saved in localStorage, wrapped in try/catch.
