# 02 — Context builder (the state Jev sees)

Deterministic code in `pipeline/state.py` builds the state. No LLM is involved, so what Jev saw is always reproducible, and the page shows it in the snapshot panel.

## Sources (all mock, in `data/snapshot.json`)
| Source | Contributes |
|---|---|
| Calendar | Current and next meeting, focus blocks, personal events (school pickup 17:30) |
| Jira | Sanad's tickets: key, title, priority, due date (CHK-88, High, due today) |
| GitHub | Sanad's open PRs and branches (PR #212 on the investor demo branch) |
| People | Each contact: name, role, relationship to Sanad (manager/leadership, team, family, bot) |
| Commitments | At most one past promise that matches this sender or a linked ticket (06). Hand-written in the snapshot, not retrieved from a database. |

## Per event
- Look up the sender in People and write it as a sentence ("Rami, junior dev on Sanad's Checkout team").
- Parse ticket keys (`[A-Z]+-\d+`) and PR numbers (`#\d+`) from the text and attach the linked item as a sentence.
- Add the time and Sanad's calendar state at that moment, as a sentence.
- If a commitment matches the sender or a linked ticket key, add one sentence (`commitment`). Otherwise omit the key.

## State shape sent to Jev (named fields, sentences, only what's relevant)
```json
{
  "now": "14:20, Sanad is in a focus block until 16:00",
  "sanad": "Product engineer at a startup; works with leadership and the Checkout team",
  "today": "Investor demo prep with the CEO at 11:00 tomorrow; school pickup at 17:30",
  "sender": "Rami, junior dev on Sanad's Checkout team",
  "channel": "Slack DM",
  "message": "hey, is checkout supposed to show 0 JOD for some users?",
  "linked_items": ["CHK-88: checkout pricing, High priority, owned by Sanad, due today"]
}
```
When the CEO writes about the deck, `commitment` is `"Sanad told the CEO the deck was final yesterday"`. Rami's checkout message has no matching commitment, so the key is absent.

For CI events, `message` is replaced by `ci`: `{ "branch", "test_name", "log_tail", "commit_message" }`. The log tail is trimmed to the error section, about 40 lines.

## Deadline fact (code, not a Jev field)
`deadline_minutes(event, snapshot) -> int | None` in `state.py`. It reads the message text and any linked ticket `due`. Phrases it understands for the demo: "today", "by HH:MM", and a ticket `due` of `today` (end of that window is 18:00). It returns minutes from the event time until that instant, or `null` when nothing matches.

The number is stored on the result as `facts.deadline_in_minutes` and read by the policy (04). It is **not** placed in the Jev state and it is not a Jev question. The clock stays in code so a model cannot talk past it. A linked ticket `due: today` uses 18:00 as the end of the window, so Rami's 14:20 note about CHK-88 is 220 minutes out and does not take the deadline row at the default 120.

## Deliberately NOT in the state
- **Interrupt budget, user settings, and `deadline_in_minutes`.** Those are code's job (04). Putting them in the state would sway Jev's judgments.
- Raw IDs, empty lists, and fields unrelated to the event.
