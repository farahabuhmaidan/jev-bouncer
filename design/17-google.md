# 17 — Real Google connections (Gmail and Google Calendar)

Added 2026-11-14. User request: add real Google Calendar and Gmail connections in code, and leave the demo as it is.

## What changes for the user
Nothing, until they connect. Without credentials, or before signing in, Doorman uses the demo calendar (16) and the seeded day's mail, exactly as before. On **Rules → Connections**:
- **Google account:** *Connect Google account* → Google's consent screen → back to the app ("Google account connected"). *Disconnect* revokes the token and forgets it.
- **Google Calendar:** once connected, reminder clashes and the Calendar page agenda come from the real primary calendar. Doorman writes to it **only** when you press *Add to Google Calendar* on a reminder; the card then links to the event.
- **Gmail:** *Fetch new mail* pulls the newest inbox mail (last day, up to 10), runs each new message through the Gmail adapter and the normal pipeline (state → Jev → policy), and puts it in Today. Each message is fetched once; *Restart the day* forgets what was fetched.

## Code
- `server/google.py`: `Google(store, env, http, now, tz)`, plain HTTPS with `httpx`, no Google SDK.
  - OAuth 2.0 authorization-code flow with `access_type=offline`, a random `state` checked on return, and refresh tokens. Scopes: `openid email`, `gmail.readonly`, `calendar.events`.
  - `calendar_events(day)`: `events.list` with `singleEvents=true` over that day in `DOORMAN_TZ`. All-day and cancelled events are skipped, and results are `{title, start, end}` like the demo calendar.
  - `insert_event(day, start, minutes, title, description)`: `events.insert`.
  - `gmail_recent(limit)`: `messages.list` (`in:inbox newer_than:1d`), then `messages.get(format=full)`, which is what `pipeline/adapters/gmail.py` already reads.
  - Every failure raises `GoogleError`. A calendar that can't be read gives the reminder `status: "error"`, never "no clashes".
- `server/calendar.py`: `clashes` / `next_free` take a `source(day)`; `server/live.place_reminder` and `process_event` take `events_on`. The app passes Google's calendar when connected, else the demo one.
- Tokens are stored in the local SQLite `kv` table (`google`), which is gitignored and survives `make seed`. The client id and secret come from `.env` (see `.env.example`).

## API
| Method + path | Returns |
|---|---|
| `GET /api/connections` | `{google: {configured, connected, account}, calendar: {source: demo\|google, account}, gmail: {source, account}}` |
| `GET /api/connections/google/start` | `307` to Google's consent screen; `400` if not configured |
| `GET /api/connections/google/callback` | `303` to `/?connected=google` or `/?connect_error=…` |
| `POST /api/connections/google/disconnect` | the new status |
| `POST /api/connections/gmail/sync` `{limit?}` | `{fetched, added:[event ids], skipped}`; `409` not connected, `502` Google failed |
| `POST /api/events/{id}/reminder` `{action:"push"}` | the reminder with `google: {id, link}`; `409` not connected |

## Setup (once)
1. Google Cloud Console → a project → enable the **Gmail API** and **Google Calendar API**.
2. OAuth consent screen: External, Testing, and add yourself as a test user.
3. Credentials → OAuth client ID → Web application, with redirect URI `http://localhost:8000/api/connections/google/callback`.
4. Put the id and secret in `.env`, restart `make app`, then Rules → Connect Google account.

## Privacy
Opt-in, local only. Mail and calendar data go to Google (to read them) and to the models (the state of each fetched email, like any message). Nothing is committed: tokens are in the gitignored database, and real mail lives only in the local Today list. The persona's context (Sanad's team, tickets, today) still comes from the fictional snapshot, so routing real mail is a demonstration, not a tuned product.

## Tests
`tests/test_google.py`: OAuth URL, state check, token exchange and refresh, calendar parsing in local time, insert, Gmail fetch, disconnect, all against a fake Google over `httpx.MockTransport`. `tests/test_api.py` § Google: the demo by default, the sign-in round trip and its errors, clashes from the real calendar, a calendar failure shown as an error, push, Gmail sync once only, disconnect, and the token surviving a re-seed.
