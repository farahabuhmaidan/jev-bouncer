# 02 — Context builder (the state Jev sees)

Deterministic code in `pipeline/state.py` builds the state. No LLM is involved, so what Jev saw is always reproducible, and the page shows it in the snapshot panel.

## Sources (all mock, in `data/snapshot.json`)
| Source | Contributes |
|---|---|
| Calendar | Current and next meeting, focus blocks, personal events (school pickup 17:30) |
| Jira | Sanad's tickets: key, title, priority, due date (CHK-88, High, due today) |
| GitHub | Sanad's open PRs and branches (PR #212 on the investor demo branch) |
| People | Each contact: name, role, relationship to Sanad (manager/leadership, team, family, bot) |

## Per event
- Look up the sender in People and write it as a sentence ("Rami, junior dev on Sanad's Checkout team").
- Parse ticket keys (`[A-Z]+-\d+`) and PR numbers (`#\d+`) from the text and attach the linked item as a sentence.
- Add the time and Sanad's calendar state at that moment, as a sentence.

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
For CI events, `message` is replaced by `ci`: `{ "branch", "test_name", "log_tail", "commit_message" }`. The log tail is trimmed to the error section, about 40 lines.

## Deliberately NOT in the state
- **Interrupt budget and user settings.** Those are code's job (04). Putting them in the state would sway Jev's judgments.
- Raw IDs, empty lists, and fields unrelated to the event.
