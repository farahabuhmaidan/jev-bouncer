# 06 — Mock data

## Persona: Sanad
Product engineer at a startup, between leadership and the Checkout team, has a family.

| Time | Context |
|---|---|
| 09:30 | Standup |
| 11:00 | Investor demo prep with the CEO |
| 14:00–16:00 | Focus block |
| All day | Owns CHK-88 (checkout pricing, High, due today); PR #212 on `investor-demo` |
| 17:30 | School pickup |
| 18:00+ | Evening mode |

## `data/events.json`: about 35 events (solo build; up to 60 with help)
```json
{
  "id": "evt-031",
  "time": "14:20",
  "type": "message",            // or "ci_failure"
  "source": "slack",            // slack | email | github_actions
  "sender": "rami",             // key into snapshot.people
  "text": "hey, is checkout supposed to show 0 JOD for some users?",
  "label": { "action": "interrupt" },
  "holdout": false,
  "demo_moment": "loud-vs-quiet" // or null
}
```
CI events have no `text`. They add `branch`, `test_name` and `log_file` (a path in `ci_logs/`), and their label adds `failure_type`.

**Mix:** about 70% batch, drop or delegate; about 6 CI failures; about 8 events with `holdout: true` spread across types.

## Demo moments (each must exist in the data)
1. **Loud vs quiet:** CEO "URGENT!!! can we make the deck blue" → batch, plus an auto-reply. Rami's quiet checkout bug about CHK-88 → interrupt.
2. **Three CI failures:** flaky (silent rerun), infra (DevOps), regression on `investor-demo` (interrupt + explanation).
3. **Unsure:** cofounder "got a sec?" with no context → `needs_sanad` lands in the unsure band → ask Sanad.
4. **Evening:** 19:10 school message → interrupt; 19:30 leadership roadmap thread → batch to morning.

## `data/snapshot.json`
```json
{
  "user": { "name": "Sanad", "role": "Product engineer", "team": "checkout" },
  "calendar": [ { "start": "14:00", "end": "16:00", "title": "Focus block", "kind": "focus" } ],
  "tickets": [ { "key": "CHK-88", "title": "Checkout pricing", "priority": "High", "due": "today", "owner": "sanad" } ],
  "prs": [ { "number": 212, "branch": "investor-demo", "title": "Demo flow polish" } ],
  "people": {
    "rami": { "name": "Rami", "role": "Junior dev", "relationship": "team", "team": "checkout", "lead": "sanad", "is_bot": false }
  },
  "devops_contact": "lina"
}
```
`kind` is one of `meeting`, `focus` or `personal`. People to include: Rami, the CEO, the cofounder, the PM, a DevOps contact, a team lead, Sanad's partner, the school, and 2–3 bots (e.g. a newsletter and a calendar bot). All names are invented.

CI events use `"sender": "github-actions"`, a bot entry in `people`.

## `data/ci_logs/`
Four to six short text logs (about 40–80 lines), each with the log tail, commit message and a small diff snippet. One log per failure type, plus the regression on `investor-demo`.

## Budget in the data
Keep labelled budget-using interrupts to **5 or fewer** at default settings, so the default budget never forces a different answer. Labels and the baseline can then both judge each event on its own. Lowering the budget in the settings is a demo of the slider, not part of the measured comparison.

## When a demo moment doesn't land
If Jev's real answers don't produce one of the 4 demo moments, **reword that event's text and rerun it**. The rules:
- Only the 4 demo-moment events may be reworded. They are never part of the holdout.
- The label stays the same; only the text changes.
- Every rewording is logged in `data/CHANGELOG.md` with the old text, the new text and why. The README's limits section links to it.

## Labelling rule
An LLM may draft event texts. **A person sets every `label`**, based on the right action for Sanad at **default settings**, before Jev runs. Labels are never edited after looking at model output, except for clear labelling mistakes, which get a note.
