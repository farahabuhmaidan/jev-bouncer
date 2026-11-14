PY := .venv/bin/python

.PHONY: install test pipeline eval demo

install:
	@if command -v uv >/dev/null; then uv venv -q --python 3.12 .venv && uv pip install -q -p .venv -r requirements.txt; \
	else python3 -m venv .venv && $(PY) -m pip install -q -r requirements.txt; fi

test:
	$(PY) -m pytest -q
	node --test 'web/*.test.js'

pipeline:
	$(PY) -m pipeline.run

eval:
	$(PY) -m pipeline.run --eval-only

demo:
	@echo "Open http://localhost:8000/web/  (slides: http://localhost:8000/slides/)"
	python3 -m http.server 8000
