PYTHON ?= python3.13
VENV ?= .venv
BIN := $(VENV)/bin

COMPOSE := docker compose

.PHONY: bootstrap compose-build compose-down compose-up contract format-check lint phase1-smoke test typecheck verify

bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e ".[dev]"

compose-build:
	$(COMPOSE) build

compose-down:
	$(COMPOSE) down

compose-up:
	$(COMPOSE) up -d --build --wait

contract:
	$(BIN)/python tools/repository_contract.py

format-check:
	$(BIN)/ruff format --check .

lint:
	$(BIN)/ruff check .

phase1-smoke:
	$(BIN)/python scripts/phase1_smoke.py --token "$(FLEETPULSE_AGENT_TOKEN)"

test:
	$(BIN)/pytest

typecheck:
	$(BIN)/mypy

verify: lint format-check typecheck test contract
