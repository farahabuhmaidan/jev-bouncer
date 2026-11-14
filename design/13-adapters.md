# 13 — Source adapters (pluggable)

Adding a new source must take **one new file, one example payload and zero changes anywhere else**. Every source becomes the same unified event before anything else sees it, so the state builder, Jev, the policy and the UI never know which source an event came from.

```
raw payload (Slack / Gmail / GitHub / …)
        │  adapter.to_event(raw, people)      ← the only source-specific code
        ▼
unified event  ──►  state builder (02) ──► Jev ──► policy …
```

## The contract (`pipeline/adapters/base.py`)
```python
class Adapter(Protocol):
    source: str                      # "slack", "gmail", "github_actions"
    event_type: str                  # "message" or "ci_failure"
    def to_event(self, raw: dict, people: dict) -> dict: ...   # pure: no network, no clock
    def fetch(self, **kwargs) -> list[dict]: ...               # optional live pull, never used during the demo
```
- `to_event` returns a **unified event**, the shape in `06-data.md`: `id, time, type, source, sender, text` (+ `subject`, `thread`, `links` when present; CI adds `branch, test_name, log_file`).
- **Registry:** `pipeline/adapters/__init__.py` holds `ADAPTERS: dict[str, Adapter]` filled by a `@register` decorator. Each adapter module is imported in that file, so adding a source is one import line plus its module.
- **Sender resolution:** each person in `snapshot.people` may carry `handles: {"slack": "U07RAMI", "email": "rami@example.com"}`. `resolve_sender(source, handle, people)` in `base.py` maps a handle to a person key. Unknown handles come back as `"unknown:<handle>"`, and the state builder already writes those as "Unknown sender" (02).
- **Text cleanup belongs to the adapter:** Slack `<@U07RAMI>` mentions become names, email HTML is stripped, quoted reply chains are cut. The state should read the way a person would see the message.

## Two kinds of adapter
- **Event adapters** (Slack, Gmail, GitHub Actions) turn incoming items into events to route.
- **Context adapters** (Calendar; later Jira, GitHub PRs) feed the background snapshot that every Jev state is built from. They follow the same pattern with a different output:
```python
class ContextAdapter(Protocol):
    source: str                      # "google_calendar"
    section: str                     # the snapshot key it fills: "calendar"
    def to_context(self, raw: dict) -> list[dict]: ...   # pure
    def fetch(self, **kwargs) -> dict: ...               # optional live pull
```
`CONTEXT_ADAPTERS` is a registry like `ADAPTERS`. `pipeline/load.py: load_snapshot(path) -> dict` reads `snapshot.json`. For every `"<section>": {"raw_source": ..., "raw": ...}` entry, it replaces the entry with `CONTEXT_ADAPTERS[raw_source].to_context(raw)`. Hand-written sections are left as they are.

| Adapter | Input shape | Output |
|---|---|---|
| `google_calendar.py` | Google Calendar API `events.list` response (`items[]` with `summary`, `start.dateTime`, `end.dateTime`, `eventType`, `transparency`, `status`) | `[{start, end, title, kind}]` in the 06 shape. `eventType: "focusTime"` → `focus`; `eventType: "outOfOffice"` → `personal`; a title matching the user's personal keywords (`snapshot.user.personal_keywords`, e.g. "pickup") → `personal`; otherwise `meeting`. Cancelled and `transparency: "transparent"` (free) events are skipped. All-day events are skipped for the demo. |

Sanad's demo calendar comes from `data/raw/google_calendar/sanad-day.json` through this adapter, so the focus block and pickup that drive demo moments are produced by the integration path, not typed into the snapshot.

The contract test covers context adapters too: for each fixture, every item has `start` and `end` as `HH:MM`, start before end, and a `kind` that is one of `meeting`, `focus` or `personal`. No network calls.

## How events.json uses adapters
An entry in `data/events.json` is either already unified (mock events) or **raw**:
```json
{ "raw_source": "slack", "raw": { "...": "a real Slack Events API payload" },
  "label": { "action": "interrupt" }, "holdout": false, "demo_moment": null }
```
The loader (`pipeline/load.py: load_events(path, snapshot) -> list[dict]`) runs `ADAPTERS[raw_source].to_event(raw, people)` for raw entries and copies `label`, `holdout` and `demo_moment` onto the result. Labels stay in one file.

## Example adapters (built for the hackathon)
| Adapter | Input shape | Notes |
|---|---|---|
| `slack.py` | Slack Events API `event_callback` with `event.type == "message"` (`user`, `text`, `ts`, `channel`, `channel_type`, `thread_ts`) | `ts` → local `HH:MM`; `channel_type: "im"` → channel "Slack DM", otherwise "Slack #<channel name from payload or id>"; mentions resolved; bot messages (`bot_id` or `subtype: "bot_message"`) map to a bot sender |
| `gmail.py` | Gmail API `users.messages.get` resource, `format=full` (`id`, `threadId`, `internalDate`, `payload.headers` From/Subject, `payload.parts[].body.data` base64url) | Text = subject + plain-text body (the `text/plain` part; else the HTML part, stripped). Quoted history after "On … wrote:" is cut. `List-Unsubscribe` header present → hint for `is_noise` (passed as a fact in the state, not decided by code) |
| `github_actions.py` | `gh run view <id> --json` output + `--log-failed` text | Produces a `ci_failure` with branch, failing test name and trimmed log. Its `fetch()` can pull a real run from this repo with `gh`; that is the one optional live source (cut first if late) |

**Every example payload is fictional** (`example.com` addresses, made-up Slack IDs) and stored in `data/raw/<source>/*.json`. Each mirrors the real API shape, so the adapter would work on a real payload unchanged.

`fetch()` for Slack and Gmail is a stub that raises `NotImplementedError("needs OAuth; see design/13")`. The README says what a real connection would need: Slack app + Events API subscription, or a Gmail push via Pub/Sub. That's an honest "plugs in here", not a claim of a live integration.

## Contract test (keeps it dynamic)
`tests/test_adapters.py` is parametrized over `ADAPTERS`. For **every** registered adapter and every fixture in `data/raw/<source>/`:
- `to_event` returns all required unified fields with the right types
- `time` matches `HH:MM`
- `sender` is a key in people, or starts with `unknown:`
- `to_event` makes no network call (the test patches `socket.socket` to raise)

So a new adapter is checked automatically, with no test edits.

## Adding a source (documented in the README)
1. Add `pipeline/adapters/<source>.py` with a `@register` class
2. Add a sample payload in `data/raw/<source>/`
3. Add handles for that source to people in `snapshot.json` if needed
4. Run `make test`
