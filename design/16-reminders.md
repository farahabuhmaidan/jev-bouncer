# 16 — Reminders from messages, checked against the calendar

Added 2026-11-14. User request: for a message like "you need to pay school fees next month", connect the calendar (a demo connection is fine), add a reminder at the time the message implies, and show clashes.

## Flow (code decides, Jev judges, the LLM writes)
1. **When (code).** `pipeline/when.resolve_when(text, today, now)` finds the first *future* date the text names: tomorrow, next week (Monday), next month (the 1st), in N days/weeks, a weekday, "3 December", "Dec 20", each with an optional "at 4pm". No time → 09:00. Same-day times stay the deadline fact's job (02). No date → no reminder and no extra model call.
2. **Is it a task for Sanad (Jev).** Only when a date was found, a second Jev request asks one Noul, `task_later` (`pipeline/questions.REMINDER_QUESTIONS`): "Does `message` ask Sanad to do something himself at a later date?" It is a separate request because it only exists when code found a date. One retry; a failed call is shown as an error, never as "no".
3. **Add (code).** `p >= yesAt` → reminder of 30 minutes at that date and time. Below → nothing.
4. **Clashes (code).** `server/calendar.py` reads Sanad's calendar (Google Calendar API `calendar#events` JSON, weekly RRULEs expanded) and lists overlapping events; `next_free` suggests the first free start at or after the reminder, before 18:00.
5. **Title (LLM).** `llm.reminder_title` writes a short title ("Pay school fees") in the background thread; until then the title is the message text.

The reminder never changes routing: the message is still routed by the policy (04). It is stored on the result as `reminder: {date, time, phrase, title, minutes, p, status: added|removed|error, clashes:[{title,start,end}], suggested}`.

## Calendar connection
Demo only: `connection()` reports Google Calendar, `sanad@example.com`, `demo: true`. The data are fictional payloads in `data/raw/google_calendar/` (`sanad-day.json`, `sanad-upcoming.json`). A real connection would fetch the same shape with the Calendar API and write the reminder with `events.insert`; nothing else changes.

## API
| Method + path | Body | Returns |
|---|---|---|
| `GET /api/calendar` | | `{connection, today, reminders:[{event_id, sender, message, ...reminder, day:[events that date]}]}` (status added, by date) |
| `POST /api/events/{id}/reminder` | `{action: move \| keep \| remove \| add}` | the updated reminder; `move` goes to `suggested` and re-checks clashes; `404` no reminder; `422` unknown action |

## UI
- **Today → message detail:** "Added to your calendar" card: date tile, title, when and the phrase it came from, a clash line ("Clashes with Quarterly planning (09:00–10:30)"), buttons **Move to 10:30** and **Remove** (then **Add it back**). The inbox row gets a "Reminder" / "Reminder · clash" tag.
- **Calendar page:** a full calendar app. A sidebar holds a mini month (reminder days dotted), calendar toggles ("Sanad (demo calendar)" or the Google account, and "Doorman reminders") and the list of reminders from messages. The main area has Today and ‹ › controls and a **Day / Week / Month** switch (week by default, day on phones). Events sit on an hour grid starting at 08:00, overlaps cascade side by side, reminders are violet with the Doorman icon, clashes have an amber outline, and a red line marks the demo clock. Clicking a reminder opens a popover with the message it came from, the clash, **Move to …**, **Add to Google Calendar** (when connected), **Open message** and **Remove**. The data comes from `GET /api/calendar/range?start=YYYY-MM-DD&days=1..42` (`{connection, today, days:[{date, events}]}`; Google in one request when connected, `502` if it fails) plus `GET /api/calendar` for the reminders.
- **Rules → Connections:** Google Calendar, connected (demo data).

## Tests
`tests/test_when.py` (phrases → dates), `tests/test_calendar.py` (recurrence, clashes, next free), `tests/test_live.py` (reminder added with clash and suggestion; none when `task_later` is low; no question without a date; error status), `tests/test_api.py` (calendar list, move, remove, 422).
