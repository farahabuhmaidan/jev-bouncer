# Data changelog

Every rewording of a demo-moment event after seeing model output is logged here (design/06).

| Date | Event | Old text | New text | Why |
|---|---|---|---|---|

## Label corrections

Labels changed after the first real run (2026-11-14), with the reason. Both models are scored against the same labels.

| Event | Old label | New label | Why |
|---|---|---|---|
| evt-021 | delegate | interrupt | A customer's discount code not applying in checkout is the live pricing bug blocking tomorrow's investor demo, not a support question. |

## Policy changes after the first real run

- Family rule: "family always interrupts" became "family can always reach me". A family message interrupts past the budget and evening mode unless Jev is sure it is not time-sensitive; then it is held for the next free slot ("bread, not urgent"). The LLM baseline prompt was updated to the same rule and its calls rerun.
- Leadership messages are held, not delegated (design/04 already said so; the code had missed it).
- An unsure `time_sensitive` asks only when Sanad is needed; when `no(needs_sanad)` the event is delegated.
