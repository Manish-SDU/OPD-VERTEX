PYTHON ?= python
UVICORN ?= uvicorn

.PHONY: install dev test lint run

install:
	$(PYTHON) -m pip install -e .[dev]

run:
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

dev: run

test:
	pytest

lint:
	@echo "TODO: add ruff/black/mypy when implementation matures."
