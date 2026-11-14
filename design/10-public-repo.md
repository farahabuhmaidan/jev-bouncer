# 10 — Public repo

This repo will be made public after the hackathon. Everything committed must be safe and readable for strangers. The layout and README follow the style of [service-buddy](https://github.com/ahmedkeewan/service-buddy): a pitch first, a quickstart that works, measured numbers with links to the raw data, and a section for engineers.

## Layout
```
README.md          pitch, demo GIF, quickstart, the numbers, how it works
LICENSE            MIT
.gitignore         .env, .venv/, __pycache__/, .DS_Store, .remember/
.env.example       OPENROUTER_API_KEY= (no value)
AGENTS.md          short guide for AI agents working in the repo (where things are, how to run)
Makefile           make install · make pipeline · make demo · make eval
design/            this spec
data/              mock persona, events, CI logs (all fictional)
pipeline/          offline Jev + LLM runs → web/results.json
web/               the static demo page
slides/            the presentation deck (see 11)
docs/assets/       demo GIF, screenshots, saved eval results
```

## Root README sections (written last, in hour 3)
1. **One-line pitch**, then a badge row and the demo GIF
2. **What it does**: three bullets (loud vs quiet, Jev judges and code decides, measured against an LLM-only baseline)
3. **Quickstart**: `git clone` → `make demo` opens the replay from the committed `results.json` with **no API keys needed**. Rerunning the models (`make pipeline`) needs keys in `.env`.
4. **The numbers**: the metrics table with date, model versions, event count and sample size, plus a link to the saved results file. Losses are shown too.
5. **How it works**: the architecture diagram from 01 and the truth table from 04, with links into `design/`
6. **Limits**: mock data only, one persona, small labelled set, the labeller is also the builder
7. **How real integrations would plug in** (adapters) and **privacy** (personal sources opt-in), plus a link to the slides in `slides/`.

## Rules for anything committed
- **No secrets.** Keys come only from env vars. `.env` is gitignored and `.env.example` has empty values. Check `git diff --cached` for key-like strings before each commit.
- **Fictional data only.** No real people, companies, Slack workspaces or logs. Persona names are invented.
- **No private links.** No internal docs, artifacts or chat links.
- **Reproducible claims.** Every number in the README links to the file it came from, and `make eval` regenerates it.
- **Prompts and questions in plain files** (`pipeline/questions.py`, `pipeline/llm.py`), so readers can audit what the models were asked.
- `pipeline/cache/` is committed (model outputs, no secrets), so `make demo` and `make eval` work without keys.
