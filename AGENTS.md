# AGENTS.md

Guide for AI agents working in this repo. The design in `design/` is the source of truth; read `design/README.md` first.

## Layout
- `pipeline/`: offline Python. `adapters/` (one module per source, auto-registered), `load.py`, `state.py` (the state Jev sees, no AI), `questions.py` (all Jev wording), `jev.py`, `llm.py` (all LLM prompts), `run.py` (writes `web/results.json`, cached in `pipeline/cache/`).
- `web/`: static page. `policy.js` (the only routing logic) and `metrics.js` are pure ES modules shared by the page, the slides and `node --test`.
- `data/`: fictional persona (`snapshot.json`), labelled events (`events.json`), raw source payloads (`raw/<source>/`), CI logs. Any label or wording change after seeing model output goes in `data/CHANGELOG.md`.
- `slides/`: the deck; slide 6 computes its numbers from `web/results.json`.

## Commands
- `make install`: Python 3.12 venv (uv if present).
- `make test`: `pytest -q` and `node --test 'web/*.test.js'`. Keep both green.
- `make eval`: rebuild `web/results.json` from the cache and print the metrics table. No network.
- `make pipeline`: calls Jev and the LLM through OpenRouter (`OPENROUTER_API_KEY` in `.env`). Costs money; ask first.
- `make demo`: serves the repo root on :8000 (`/web/`, `/slides/`).

## Rules
- Jev answers judgments; code decides; the LLM only writes text. Don't ask a model for the routing decision in product code.
- Labels never feed the product: they are only read by `metrics.js`.
- A failed model call is an error, never a "no".
- Public repo: no secrets, no real people or private links, fictional data only.
- Write tests first (`tests/` for Python, `web/*.test.js` for JS).
