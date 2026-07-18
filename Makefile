PYTHON ?= python3.13
VENV ?= .venv
BIN := $(VENV)/bin

COMPOSE := docker compose

.PHONY: assistant-eval assistant-up bootstrap clean-clone compose-build compose-down compose-up contract final-gate format-check image-build image-scan k3d-down k3d-up k8s-build k8s-validate kind-down kind-up lint lock performance-matrix performance-smoke phase1-smoke phase2-smoke reliability-drills reliability-smoke security-static test typecheck verify

assistant-eval:
	$(BIN)/python tools/assistant_accuracy.py

assistant-up:
	$(COMPOSE) --profile ai up -d --build --wait assistant

bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip==26.0.1
	$(BIN)/python -m pip install --require-hashes -r requirements-dev.lock
	$(BIN)/python -m pip install --no-deps -e .

clean-clone:
	./scripts/ci/clean_clone_gate.sh

compose-build:
	$(COMPOSE) build

compose-down:
	$(COMPOSE) down

compose-up:
	$(COMPOSE) up -d --build --wait

k8s-build:
	./scripts/k8s/build_images.sh phase5

k8s-validate:
	kubectl kustomize deploy/kubernetes/overlays/kind >/dev/null
	kubectl kustomize deploy/kubernetes/overlays/k3d >/dev/null
	kubectl kustomize deploy/kubernetes/overlays/kind | kubeconform -strict -summary
	kubectl kustomize deploy/kubernetes/overlays/k3d | kubeconform -strict -summary
	$(BIN)/python tools/kubernetes_contract.py

kind-up: k8s-build k8s-validate
	./scripts/k8s/kind_up.sh

kind-down:
	kind delete cluster --name fleetpulse

k3d-up: k8s-build k8s-validate
	./scripts/k8s/k3d_up.sh

k3d-down:
	k3d cluster delete fleetpulse

local-tls:
	./scripts/generate_local_tls.sh

contract:
	$(BIN)/python tools/repository_contract.py

format-check:
	$(BIN)/ruff format --check .

lint:
	$(BIN)/ruff check .

lock:
	$(BIN)/python -m pip install pip-tools==7.5.3
	$(BIN)/pip-compile --generate-hashes --strip-extras --output-file=requirements.lock pyproject.toml
	$(BIN)/pip-compile --generate-hashes --strip-extras --extra dev --output-file=requirements-dev.lock pyproject.toml

image-build:
	./scripts/security/build_images.sh phase9

image-scan: image-build
	./scripts/security/scan_images.sh phase9 artifacts/supply-chain

phase1-smoke:
	$(BIN)/python scripts/phase1_smoke.py --token "$(FLEETPULSE_AGENT_TOKEN)"

phase2-smoke:
	$(BIN)/python scripts/phase2_smoke.py --token "$(FLEETPULSE_AGENT_TOKEN)"

performance-smoke:
	$(BIN)/python tools/performance_runner.py --profile smoke

performance-matrix:
	$(BIN)/python tools/performance_runner.py --profile full

reliability-smoke:
	$(BIN)/python tools/reliability_runner.py --incident-repetitions 1

reliability-drills:
	$(BIN)/python tools/reliability_runner.py --incident-repetitions 5

security-static:
	./scripts/security/static_gate.sh

test:
	$(BIN)/pytest

typecheck:
	$(BIN)/mypy

verify: lint format-check typecheck test contract
	$(BIN)/python tools/assistant_accuracy.py >/dev/null
	$(BIN)/python tools/ci_contract.py
	$(BIN)/python tools/evidence_claims.py

final-gate: verify security-static image-scan
