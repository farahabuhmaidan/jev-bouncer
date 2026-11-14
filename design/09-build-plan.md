# 09 — 3-hour build plan

Team: one person plus an AI coding agent, so about 35 events. Order matters: data and the Jev call shape come first, because everything depends on them.

| Clock | Work | Done when |
|---|---|---|
| 0:00–0:20 | Read the TypeSafe docs (API, primitives, models). Make one Jev test call and one Anthropic call | Both return. Request shape noted in `questions.py` |
| 0:00–0:50 | `snapshot.json`, about 35 events with labels, 4–6 CI logs (the agent drafts, a person labels) | All 4 demo moments present; every event labelled |
| 0:20–1:30 | `state.py` (state, one commitment, `deadline_minutes`), `questions.py`, `run.py` (Jev answers + baseline answers + auto-replies + CI explanation + digest, cached) | `results.json` has both answer sets and a deadline fact for every event |
| 1:00–2:15 | `index.html`, `policy.js` (including the deadline row), feed, snapshot panel, phone, settings drawer, replay controls | Day replays; a settings change re-routes both columns |
| 2:15–2:35 | `metrics.js` (critical misses and interrupt precision first), metrics strip, sender view, digest overlay | Real numbers on screen |
| 1:30–2:00 | Slides (see 11): the agent drafts all slides while the page is being built; numbers stay as placeholders | Deck opens; only the numbers slide is unfilled |
| 2:35–2:45 | Fill the numbers slide from `results.json`; root `README.md`, `LICENSE`, `.env.example`, `Makefile` (see 10) | A stranger can `make demo` without keys |
| 2:45–3:00 | Rehearse slides → live demo → numbers twice; record a backup video | Video saved |

## Cut order if late
1. Optional "model picks the action" call (05) → 2. Calibration → 3. Live button → 4. Deadline parsing, if it breaks (`deadline_in_minutes` stays null and row 5 never fires) → 5. Sender view (keep auto-replies in the feed) → 6. Digest → 7. Rising bar.
Never cut: the snapshot + why panel, the settings drawer, the metrics strip.

## Risks
| Risk | Fallback |
|---|---|
| Jev request shape differs from this spec | Adapt `questions.py` in the first 20 min; the design doesn't depend on exact names |
| Jev misreads long CI logs | Trim to the error section, test name and first stack frames |
| Jev doesn't beat the LLM on accuracy | Lead with critical misses, interrupt precision, cost and latency; show the honest table |
| An API is down at demo time | Nothing is live; `results.json` is committed; backup video |
| Privacy questions about family messages | Mock data only; a slide says personal sources are opt-in |

## Open items
- Hackathon rules on code written before the clock started (affects whether data can be pre-made)
- Final product and repo name
