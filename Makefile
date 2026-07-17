PYTHON ?= python3.13
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: bootstrap contract format-check lint test typecheck verify

bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e ".[dev]"

contract:
	$(BIN)/python tools/repository_contract.py

format-check:
	$(BIN)/ruff format --check .

lint:
	$(BIN)/ruff check .

test:
	$(BIN)/pytest

typecheck:
	$(BIN)/mypy

verify: lint format-check typecheck test contract

