#!/usr/bin/env python3
"""Assert FleetPulse Kubernetes operational and security invariants."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
OVERLAYS = ("kind", "k3d")
REQUIRED_DEPLOYMENTS = {
    "api",
    "worker",
    "outbox-relay",
    "nginx",
    "prometheus",
    "alertmanager",
    "grafana",
}
PRIVATE_SERVICES = {"postgres", "redis", "prometheus", "alertmanager", "grafana"}


def render(overlay: str) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["kubectl", "kustomize", str(ROOT / "deploy/kubernetes/overlays" / overlay)],
        check=True,
        capture_output=True,
        text=True,
    )
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_workload(document: dict[str, Any]) -> None:
    kind = document["kind"]
    name = document["metadata"]["name"]
    pod_spec = document["spec"]["template"]["spec"]
    for container in pod_spec["containers"]:
        resources = container.get("resources", {})
        require(resources.get("requests"), f"{kind}/{name} lacks resource requests")
        require(resources.get("limits"), f"{kind}/{name} lacks resource limits")
        require(container.get("readinessProbe"), f"{kind}/{name} lacks a readiness probe")
        require(container.get("livenessProbe"), f"{kind}/{name} lacks a liveness probe")
    if kind == "Deployment" and name in {"api", "worker", "outbox-relay", "nginx"}:
        require(
            document["spec"].get("strategy", {}).get("type") == "RollingUpdate",
            f"Deployment/{name} must use RollingUpdate",
        )


def check_overlay(overlay: str) -> None:
    documents = render(overlay)
    require(not any(item["kind"] == "Secret" for item in documents), "rendered secrets forbidden")

    deployments = {item["metadata"]["name"] for item in documents if item["kind"] == "Deployment"}
    require(deployments >= REQUIRED_DEPLOYMENTS, f"{overlay} is missing deployments")
    require(
        any(
            item["kind"] == "DaemonSet" and item["metadata"]["name"] == "agent"
            for item in documents
        ),
        f"{overlay} is missing the agent DaemonSet",
    )

    for item in documents:
        if item["kind"] in {"Deployment", "DaemonSet", "StatefulSet"}:
            check_workload(item)

    services = {item["metadata"]["name"]: item for item in documents if item["kind"] == "Service"}
    require(services["nginx"]["spec"].get("type") == "NodePort", "Nginx must be local NodePort")
    for name in PRIVATE_SERVICES:
        require(
            services[name]["spec"].get("type", "ClusterIP") == "ClusterIP",
            f"Service/{name} must remain ClusterIP",
        )

    policies = {
        item["metadata"]["name"]: item for item in documents if item["kind"] == "NetworkPolicy"
    }
    require("default-deny" in policies, "default-deny NetworkPolicy is required")
    require(
        policies["default-deny"]["spec"]["podSelector"] == {}, "default-deny must select all pods"
    )

    serialized = yaml.safe_dump_all(documents)
    require("fleetpulse-runtime" in serialized, "runtime secret reference is required")
    require("fleetpulse-tls" in serialized, "TLS secret reference is required")


def main() -> int:
    for overlay in OVERLAYS:
        check_overlay(overlay)
    print("Kubernetes contract satisfied: kind and k3d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
