PY := .venv/bin/python

.PHONY: install test pipeline eval demo seed app dev frontend

install:
	cd frontend && npm install --no-audit --no-fund
	@if command -v uv >/dev/null; then uv venv -q --python 3.12 .venv && uv pip install -q -p .venv -r requirements.txt; \
	else python3 -m venv .venv && $(PY) -m pip install -q -r requirements.txt; fi

test:
	$(PY) -m pytest -q

pipeline:
	$(PY) -m pipeline.run

eval:
	$(PY) -m pipeline.run --eval-only
	$(PY) -m server.print_metrics

demo: app

seed:
	$(PY) -c "from server.db import Store, seed_store; seed_store(Store()); print('seeded data/doorman.db')"

frontend:
	cd frontend && npm run build

app: frontend
	@echo "Doorman on http://localhost:8000  (phone: /phone, slides: /slides/)"
	$(PY) -m uvicorn server.app:main_app --factory --host 0.0.0.0 --port 8000

dev:
	@echo "API on :8000, Vite on http://localhost:5173"
	$(PY) -m uvicorn server.app:main_app --factory --reload --port 8000 & cd frontend && npm run dev
