.PHONY: install bootstrap audit test lint format check

install:
	python -m pip install -e ".[dev]"

bootstrap:
	./scripts/bootstrap.sh

audit:
	python -m ai_engineering_bootstrap.cli audit

test:
	python -m pytest

lint:
	python -m ruff check .

format:
	python -m ruff format .

check: lint test audit
