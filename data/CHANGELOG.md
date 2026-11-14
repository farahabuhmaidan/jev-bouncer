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

## Same-policy comparison (design update, 2026-11-14)

Applied before rerunning either model on the changes below.
- **New event evt-034:** a daytime customer email from Hadi (Cedar Market, new fictional person), a raw Gmail payload with a deadline the clock can read ("before 15:00", sent 13:20). Labelled `interrupt` by hand before any model saw it.
- **Commitments in the snapshot:** "Sanad told the CEO the deck was final yesterday", added to the state only for Layla's messages about the deck or slides (evt-014). It is scoped by topic, so it is not added to her board-update or roadmap messages. This changes evt-014's state, so Jev is rerun for it.
- **Deadline row (policy row 5):** a deadline under `deadlineMinutes` (default 120) that code parses from the text or a linked ticket interrupts without spending budget, unless the event is noise. Rows 5–9 became 6–10.
- **Baseline:** the LLM no longer picks the action. It answers the same questions as Jev, and the same policy routes both answer sets, at the same settings. The old one-prompt router and its numbers are retired.

## Family rule: loud is not urgent (2026-11-14)

A live test message from Maha, "URGENT!!! the SHEIN discount code is going to expire in 3 hours", interrupted Sanad. Jev read it correctly as wording-only urgency (0.73), but rule 1 only held family messages when `no(time_sensitive)`, and Jev was not sure it could wait (0.74, an expiring discount reads as "money is lost"). Rule 1 now also holds a family message when `yes(wording_only_urgency)`. No labelled event changes outcome for either model, so the numbers are unchanged.
