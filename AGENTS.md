# AGENTS.md

Guide for AI agents working in this repo. The design in `design/` is the source of truth; start with `design/README.md` and `design/14-app.md`.

## Layout
- `server/`: FastAPI app. `app.py` (routes), `db.py` (SQLite store + seeding), `live.py` (a new event: state → Jev → policy, LLM text in a thread), `policy.py` (**the only routing logic**), `metrics.py`, `print_metrics.py`.
- `pipeline/`: Python shared with the server. `adapters/` (one module per source, auto-registered), `load.py`, `state.py` (the state Jev sees, no AI), `questions.py` (all Jev wording), `jev.py`, `llm.py` (all LLM prompts), `run.py` (offline run over the labelled day, cached in `pipeline/cache/`, writes `data/results.json`).
- `frontend/`: React + Vite (plain JS). Talks to the API only; never routes.
- `data/`: fictional persona (`snapshot.json`), labelled events (`events.json`), raw payloads (`raw/<source>/`), CI logs, `results.json`. Label or wording changes after seeing model output go in `data/CHANGELOG.md`. `doorman.db` is local and gitignored.
- `slides/`: the deck; slide 6 reads `/api/metrics`.

## Commands
- `make install`: Python 3.12 venv (uv if present) + `npm install` in `frontend/`.
- `make test`: `pytest -q`. Keep it green.
- `make app`: build the frontend, serve everything on :8000. `make dev` for hot reload.
- `make eval`: rebuild `data/results.json` from the cache and print the metrics table. No network.
- `make pipeline`: calls Jev and the LLM through OpenRouter (`OPENROUTER_API_KEY` in `.env`). Costs money; ask first.

## Rules
- Jev answers judgments; code decides; the LLM only writes text. Don't ask a model for the routing decision.
- Labels never feed the product: only `metrics.py` reads them.
- A failed model call is an error, never a "no".
- Public repo: no secrets, no real people or private links, fictional data only. Commits without AI co-author lines.
- Write tests first (`tests/`).
