"""Execute isolated Phase 7 failure, detection, and recovery drills."""

from __future__ import annotations

import argparse
import json
import os
import platform
import secrets
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import httpx

from fleetpulse_project.reliability import nearest_rank_percentile

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class ReliabilityHarness:
    def __init__(self, output: Path, incident_repetitions: int) -> None:
        self.output = output
        self.incident_repetitions = incident_repetitions
        self.project_name = f"fleetpulse-p7-{uuid4().hex[:8]}"
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "FLEETPULSE_AGENT_TOKEN": secrets.token_urlsafe(32),
                "FLEETPULSE_POSTGRES_PASSWORD": secrets.token_urlsafe(32),
            }
        )
        self.token = self.environment["FLEETPULSE_AGENT_TOKEN"]
        self.timeline_path = output / "timeline.jsonl"
        self.api: httpx.Client | None = None
        self.prometheus = httpx.Client(base_url="http://localhost:9090", timeout=5)

    def command(
        self, arguments: list[str], *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            arguments,
            cwd=ROOT,
            env=self.environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and completed.returncode != 0:
            details = "\n".join(
                part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
            )
            raise RuntimeError(f"command failed ({' '.join(arguments)}):\n{details}")
        return completed

    def compose(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.command(["docker", "compose", "-p", self.project_name, *arguments], check=check)

    def record(self, event: str, **details: object) -> None:
        with self.timeline_path.open("a") as stream:
            stream.write(
                json.dumps({"recorded_at": utc_now(), "event": event, **details}, sort_keys=True)
                + "\n"
            )

    def setup(self) -> None:
        self.output.mkdir(parents=True, exist_ok=False)
        self.command(["./scripts/generate_local_tls.sh"])
        self.api = httpx.Client(
            base_url="https://localhost:8443",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=10,
            verify=str(ROOT / "certs/generated/ca.crt"),
        )
        self.compose("build", "api", "worker", "outbox-relay")
        self.compose(
            "up",
            "-d",
            "--wait",
            "--wait-timeout",
            "120",
            "postgres",
            "redis",
            "api",
            "worker",
            "outbox-relay",
            "nginx",
            "prometheus",
            "alertmanager",
        )
        self.wait_api()
        self.wait_prometheus()
        self.record("environment_ready", compose_project=self.project_name)

    def wait_api(self, timeout: float = 60) -> None:
        if self.api is None:
            raise RuntimeError("API client is not initialized")
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                response = self.api.get("/readyz")
                response.raise_for_status()
                return
            except (httpx.HTTPError, OSError) as error:
                last_error = error
                time.sleep(0.25)
        raise RuntimeError(f"API did not become ready: {last_error}")

    def wait_prometheus(self) -> None:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                response = self.prometheus.get("/-/ready")
                response.raise_for_status()
                return
            except httpx.HTTPError:
                time.sleep(0.25)
        raise RuntimeError("Prometheus did not become ready")

    def psql(self, sql: str) -> str:
        return self.compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "fleetpulse",
            "-d",
            "fleetpulse",
            "-Atc",
            sql,
        ).stdout.strip()

    def firing_alert(self, alert_name: str) -> dict[str, Any] | None:
        response = self.prometheus.get("/api/v1/alerts")
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        for alert in payload["data"]["alerts"]:
            if alert["labels"].get("alertname") == alert_name and alert["state"] == "firing":
                return cast(dict[str, Any], alert)
        return None

    def wait_alert(self, alert_name: str, *, firing: bool, timeout: float = 90) -> float:
        started = time.monotonic()
        deadline = started + timeout
        while time.monotonic() < deadline:
            alert = self.firing_alert(alert_name)
            if (alert is not None) is firing:
                elapsed = time.monotonic() - started
                self.record(
                    "alert_transition",
                    alert=alert_name,
                    state="firing" if firing else "clear",
                    elapsed_seconds=elapsed,
                    evidence=alert,
                )
                return elapsed
            time.sleep(0.25)
        expected = "firing" if firing else "clear"
        raise RuntimeError(f"{alert_name} did not become {expected} before timeout")

    @staticmethod
    def telemetry_payload(agent_id: str, cpu_percent: float) -> tuple[str, dict[str, object]]:
        batch_id = str(uuid4())
        return batch_id, {
            "schema_version": 1,
            "batch_id": batch_id,
            "agent_id": agent_id,
            "hostname": f"{agent_id}-host",
            "samples": [
                {
                    "observed_at": utc_now(),
                    "cpu_percent": cpu_percent,
                    "load_1m": 1,
                    "load_5m": 1,
                    "load_15m": 1,
                    "memory": {
                        "total_bytes": 1024,
                        "available_bytes": 512,
                        "used_bytes": 512,
                        "used_percent": 50,
                    },
                    "disks": [
                        {
                            "mount": "/",
                            "total_bytes": 1024,
                            "used_bytes": 512,
                            "free_bytes": 512,
                            "used_percent": 50,
                        }
                    ],
                    "network": {
                        "bytes_sent": 1,
                        "bytes_received": 1,
                        "packets_sent": 1,
                        "packets_received": 1,
                        "errors_in": 0,
                        "errors_out": 0,
                        "drops_in": 0,
                        "drops_out": 0,
                        "tcp_established": 1,
                        "tcp_listening": 1,
                        "tcp_other": 0,
                        "udp_sockets": 0,
                    },
                    "process_count": 1,
                    "top_processes": [],
                }
            ],
        }

    def post_telemetry(self, agent_id: str, cpu_percent: float) -> str:
        if self.api is None:
            raise RuntimeError("API client is not initialized")
        batch_id, payload = self.telemetry_payload(agent_id, cpu_percent)
        response = self.api.post(
            "/v1/telemetry/batches",
            json=payload,
            headers={"X-Request-ID": f"phase7-{agent_id}"},
        )
        response.raise_for_status()
        if response.json()["status"] != "accepted":
            raise RuntimeError("drill telemetry was not newly accepted")
        return batch_id

    def api_outage_drill(self) -> dict[str, float]:
        self.wait_alert("FleetPulseAPITargetDown", firing=False)
        self.compose("stop", "api")
        injected = time.monotonic()
        self.record("failure_injected", drill="api_outage", action="api stopped")
        detection = self.wait_alert("FleetPulseAPITargetDown", firing=True)
        repair_started = time.monotonic()
        self.compose("up", "-d", "--wait", "--wait-timeout", "90", "api")
        self.wait_api()
        repair_recovery = time.monotonic() - repair_started
        total_impact = time.monotonic() - injected
        alert_clear = self.wait_alert("FleetPulseAPITargetDown", firing=False)
        self.record(
            "recovery_complete",
            drill="api_outage",
            repair_recovery_seconds=repair_recovery,
            total_impact_seconds=total_impact,
        )
        return {
            "alert_detection_seconds": detection,
            "repair_recovery_seconds": repair_recovery,
            "total_impact_seconds": total_impact,
            "alert_clear_seconds": alert_clear,
        }

    def wait_incident(self, agent_id: str, timeout: float = 30) -> float:
        if self.api is None:
            raise RuntimeError("API client is not initialized")
        started = time.monotonic()
        deadline = started + timeout
        while time.monotonic() < deadline:
            response = self.api.get("/v1/incidents")
            response.raise_for_status()
            if any(item["agent_id"] == agent_id for item in response.json()):
                return time.monotonic() - started
            time.sleep(0.1)
        raise RuntimeError(f"incident for {agent_id} did not become queryable")

    def incident_drills(self) -> dict[str, object]:
        trials: list[dict[str, float | int]] = []
        for repetition in range(1, self.incident_repetitions + 1):
            self.wait_alert("FleetPulseIncidentDetected", firing=False)
            agent_id = f"phase7-incident-{repetition}"
            accepted_at = time.monotonic()
            self.post_telemetry(agent_id, 99)
            visible = self.wait_incident(agent_id)
            alert = self.wait_alert("FleetPulseIncidentDetected", firing=True)
            end_to_end = time.monotonic() - accepted_at
            self.record(
                "incident_detected",
                drill="threshold_incident",
                repetition=repetition,
                incident_visibility_seconds=visible,
                alert_detection_seconds=alert,
                end_to_end_seconds=end_to_end,
            )
            trials.append(
                {
                    "repetition": repetition,
                    "incident_visibility_seconds": visible,
                    "alert_detection_seconds": alert,
                    "end_to_end_seconds": end_to_end,
                }
            )
            self.wait_alert("FleetPulseIncidentDetected", firing=False)
        p95 = nearest_rank_percentile([float(trial["end_to_end_seconds"]) for trial in trials], 95)
        return {"trials": trials, "p95_end_to_end_seconds": p95, "target_seconds": 60}

    def redis_outage_drill(self) -> dict[str, float | int | str]:
        self.wait_alert("FleetPulseOutboxFailure", firing=False)
        self.compose("stop", "redis")
        injected = time.monotonic()
        self.record("failure_injected", drill="redis_outage", action="redis stopped")
        batch_id = self.post_telemetry("phase7-redis-outage", 40)
        durable_rows = int(
            self.psql(f"SELECT count(*) FROM telemetry_batches WHERE batch_id = '{batch_id}';")
        )
        if durable_rows != 1:
            raise RuntimeError("telemetry was not durable during Redis outage")
        detection = self.wait_alert("FleetPulseOutboxFailure", firing=True)
        repair_started = time.monotonic()
        self.compose("up", "-d", "--wait", "--wait-timeout", "60", "redis")
        deadline = time.monotonic() + 60
        processed = 0
        while time.monotonic() < deadline:
            processed = int(
                self.psql(
                    "SELECT count(*) FROM outbox_events o "
                    "JOIN processed_events p ON p.event_id = o.event_id "
                    f"WHERE o.aggregate_id = '{batch_id}' AND o.published_at IS NOT NULL;"
                )
            )
            if processed == 1:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("durable Redis-outage event did not recover")
        unpublished = int(
            self.psql(
                "SELECT count(*) FROM outbox_events "
                f"WHERE aggregate_id = '{batch_id}' AND published_at IS NULL;"
            )
        )
        dead_letters = int(self.psql("SELECT count(*) FROM dead_letters;"))
        if unpublished != 0 or dead_letters != 0:
            raise RuntimeError("Redis recovery left unpublished or dead-lettered drill state")
        repair_recovery = time.monotonic() - repair_started
        total_impact = time.monotonic() - injected
        alert_clear = self.wait_alert("FleetPulseOutboxFailure", firing=False)
        self.record(
            "recovery_complete",
            drill="redis_outage",
            batch_id=batch_id,
            repair_recovery_seconds=repair_recovery,
            total_impact_seconds=total_impact,
        )
        return {
            "batch_id": batch_id,
            "durable_rows_during_outage": durable_rows,
            "processed_after_recovery": processed,
            "unpublished_after_recovery": unpublished,
            "dead_letters_after_recovery": dead_letters,
            "alert_detection_seconds": detection,
            "repair_recovery_seconds": repair_recovery,
            "total_impact_seconds": total_impact,
            "alert_clear_seconds": alert_clear,
        }

    def metadata(self) -> dict[str, object]:
        def output(arguments: list[str]) -> str:
            return self.command(arguments).stdout.strip()

        return {
            "recorded_at": utc_now(),
            "repository": str(ROOT),
            "git_commit": output(["git", "rev-parse", "HEAD"]),
            "git_worktree_dirty": bool(output(["git", "status", "--porcelain"])),
            "compose_project": self.project_name,
            "incident_repetitions": self.incident_repetitions,
            "host": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "logical_cpus": os.cpu_count(),
            },
            "docker_version": output(["docker", "version", "--format", "{{.Server.Version}}"]),
            "prometheus_intervals": {"scrape_seconds": 5, "evaluation_seconds": 5},
            "credentials": "ephemeral and excluded from evidence",
        }

    def capture_runtime(self) -> None:
        (self.output / "compose-ps.txt").write_text(self.compose("ps", "-a", check=False).stdout)
        (self.output / "compose-logs.txt").write_text(
            self.compose("logs", "--no-color", check=False).stdout
        )
        try:
            alerts = self.prometheus.get("/api/v1/alerts")
            if alerts.is_success:
                write_json(self.output / "final-alerts.json", alerts.json())
        except httpx.HTTPError:
            self.record("final_alert_capture_unavailable")

    def run(self) -> dict[str, object]:
        return {
            "api_outage": self.api_outage_drill(),
            "threshold_incidents": self.incident_drills(),
            "redis_outage": self.redis_outage_drill(),
        }

    def close(self) -> None:
        try:
            if self.output.exists():
                self.capture_runtime()
        finally:
            if self.api is not None:
                self.api.close()
            self.prometheus.close()
            self.compose("down", "--volumes", check=False)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--incident-repetitions", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if arguments.incident_repetitions < 1:
        raise ValueError("incident repetitions must be positive")
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = (arguments.output or ROOT / "evidence/runs" / f"{timestamp}-phase-7").resolve()
    harness = ReliabilityHarness(output, int(arguments.incident_repetitions))
    try:
        harness.setup()
        metadata = harness.metadata()
        results = harness.run()
        write_json(output / "metadata.json", metadata)
        write_json(output / "results.json", results)
    except Exception as error:
        if output.exists():
            write_json(
                output / "failure.json",
                {"failed_at": utc_now(), "error_type": type(error).__name__, "message": str(error)},
            )
        raise
    finally:
        harness.close()
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
