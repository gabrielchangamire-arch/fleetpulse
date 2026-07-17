"""Run the controlled local Phase 6 performance experiments.

The harness deliberately compares one variable at a time. It keeps the API tier
fixed while measuring cache behavior, then keeps ingestion fixed while measuring
one versus four Redis Stream workers.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import platform
import secrets
import shutil
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from fleetpulse_project.performance import aggregate_results, k6_metrics, parse_bytes, parse_percent

ROOT = Path(__file__).resolve().parents[1]
K6_SCRIPT = ROOT / "load/k6/fleetpulse.js"
SERVICES = ("postgres", "redis", "api", "worker", "outbox-relay", "nginx")
TRUNCATE_SQL = """
TRUNCATE TABLE dead_letters, processed_events, deployments, incidents, fleet_state,
outbox_events, telemetry_batches, agents RESTART IDENTITY CASCADE;
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class PerformanceHarness:
    def __init__(self, output: Path, repetitions: int, keep_running: bool) -> None:
        self.output = output
        self.repetitions = repetitions
        self.keep_running = keep_running
        self.project_name = f"fleetpulse-p6-{uuid4().hex[:8]}"
        self.results: list[dict[str, Any]] = []
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "FLEETPULSE_AGENT_TOKEN": secrets.token_urlsafe(32),
                "FLEETPULSE_POSTGRES_PASSWORD": secrets.token_urlsafe(32),
                "FLEETPULSE_CACHE_ENABLED": "true",
            }
        )
        self.token = self.environment["FLEETPULSE_AGENT_TOKEN"]
        self.client = httpx.Client(
            base_url="https://localhost:8443",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=10,
            verify=str(ROOT / "certs/generated/ca.crt"),
        )

    def command(
        self,
        arguments: list[str],
        *,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            arguments,
            cwd=ROOT,
            env=env or self.environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and completed.returncode != 0:
            message = "\n".join(
                part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
            )
            raise RuntimeError(f"command failed ({' '.join(arguments)}):\n{message}")
        return completed

    def compose(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.command(["docker", "compose", "-p", self.project_name, *arguments], check=check)

    def psql(self, sql: str) -> str:
        result = self.compose(
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
        )
        return result.stdout.strip()

    def redis(self, *arguments: str, check: bool = True) -> str:
        result = self.compose("exec", "-T", "redis", "redis-cli", "--raw", *arguments, check=check)
        return result.stdout.strip()

    def setup(self) -> None:
        self.output.mkdir(parents=True, exist_ok=False)
        (self.output / "raw").mkdir()
        if shutil.which("k6") is None:
            raise RuntimeError("k6 is required; install it before running Phase 6")
        if not (ROOT / "certs/generated/ca.crt").exists():
            self.command(["./scripts/generate_local_tls.sh"])
            self.client.close()
            self.client = httpx.Client(
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
            "--scale",
            "api=2",
            "postgres",
            "redis",
            "api",
            "nginx",
        )
        self.wait_api()

    def wait_api(self) -> None:
        deadline = time.monotonic() + 60
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                response = self.client.get("/readyz")
                response.raise_for_status()
                return
            except (httpx.HTTPError, OSError) as error:
                last_error = error
                time.sleep(0.5)
        raise RuntimeError(f"API did not become ready: {last_error}")

    def reset_state(self) -> None:
        self.compose("stop", "worker", "outbox-relay", check=False)
        self.compose("rm", "-f", "-s", "worker", "outbox-relay", check=False)
        self.psql(TRUNCATE_SQL)
        self.redis("FLUSHDB")

    def configure_cache(self, enabled: bool) -> None:
        self.environment["FLEETPULSE_CACHE_ENABLED"] = str(enabled).lower()
        self.compose(
            "up",
            "-d",
            "--wait",
            "--wait-timeout",
            "120",
            "--force-recreate",
            "--scale",
            "api=2",
            "api",
            "nginx",
        )
        self.wait_api()

    def seed_fleet_state(self) -> None:
        self.compose("up", "-d", "--scale", "worker=1", "worker", "outbox-relay")
        payload = self.telemetry_payload("phase6-seed", str(uuid4()))
        response = self.client.post(
            "/v1/telemetry/batches",
            json=payload,
            headers={"X-Request-ID": "phase6-seed"},
        )
        response.raise_for_status()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if self.psql("SELECT count(*) FROM fleet_state;") == "1":
                self.compose("stop", "worker", "outbox-relay")
                self.compose("rm", "-f", "-s", "worker", "outbox-relay")
                return
            time.sleep(0.25)
        raise RuntimeError("seed telemetry did not produce fleet state")

    @staticmethod
    def telemetry_payload(agent_id: str, batch_id: str) -> dict[str, object]:
        return {
            "schema_version": 1,
            "batch_id": batch_id,
            "agent_id": agent_id,
            "hostname": f"{agent_id}-host",
            "samples": [
                {
                    "observed_at": utc_now(),
                    "cpu_percent": 42,
                    "load_1m": 0.4,
                    "load_5m": 0.3,
                    "load_15m": 0.2,
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

    def container_services(self) -> dict[str, str]:
        result = self.command(
            [
                "docker",
                "ps",
                "--filter",
                f"label=com.docker.compose.project={self.project_name}",
                "--format",
                "{{.Names}}",
            ]
        )
        mapping: dict[str, str] = {}
        for name in result.stdout.splitlines():
            if not name:
                continue
            service = self.command(
                [
                    "docker",
                    "inspect",
                    "--format",
                    '{{ index .Config.Labels "com.docker.compose.service" }}',
                    name,
                ]
            ).stdout.strip()
            if service in SERVICES:
                mapping[name] = service
        return mapping

    def sample_resources(self, path: Path, stop: threading.Event) -> None:
        sample_id = 0
        while not stop.is_set():
            try:
                mapping = self.container_services()
                if mapping:
                    stats = self.command(
                        [
                            "docker",
                            "stats",
                            "--no-stream",
                            "--format",
                            "{{json .}}",
                            *mapping,
                        ]
                    )
                    sampled_at = utc_now()
                    with path.open("a") as stream:
                        for line in stats.stdout.splitlines():
                            if not line.strip():
                                continue
                            value: dict[str, str] = json.loads(line)
                            name = value["Name"]
                            used = value["MemUsage"].split("/", maxsplit=1)[0]
                            record = {
                                "sample_id": sample_id,
                                "sampled_at": sampled_at,
                                "container": name,
                                "service": mapping[name],
                                "cpu_percent": parse_percent(value["CPUPerc"]),
                                "memory_bytes": parse_bytes(used),
                            }
                            stream.write(json.dumps(record, sort_keys=True) + "\n")
                sample_id += 1
            except (
                KeyError,
                ValueError,
                json.JSONDecodeError,
                subprocess.SubprocessError,
            ) as error:
                with (path.parent / "resource-sampler-errors.txt").open("a") as stream:
                    stream.write(f"{utc_now()} {type(error).__name__}: {error}\n")
            stop.wait(1)

    def run_k6(
        self,
        directory: Path,
        *,
        mode: str,
        rate: int,
        duration: str,
        run_id: str,
        resource_path: Path,
    ) -> dict[str, float]:
        directory.mkdir(parents=True, exist_ok=True)
        raw_path = directory / "k6-samples.jsonl"
        summary_path = directory / "k6-summary.json"
        k6_environment = self.environment.copy()
        k6_environment.update(
            {
                "BASE_URL": "https://localhost:8443",
                "TOKEN": self.token,
                "MODE": mode,
                "RATE": str(rate),
                "DURATION": duration,
                "RUN_ID": run_id,
            }
        )
        stop = threading.Event()
        sampler = threading.Thread(
            target=self.sample_resources, args=(resource_path, stop), daemon=True
        )
        sampler.start()
        try:
            completed = self.command(
                [
                    "k6",
                    "run",
                    "--quiet",
                    "--summary-export",
                    str(summary_path),
                    "--out",
                    f"json={raw_path}",
                    str(K6_SCRIPT),
                ],
                check=False,
                env=k6_environment,
            )
        finally:
            stop.set()
            sampler.join(timeout=10)
        (directory / "k6-console.txt").write_text(completed.stdout + completed.stderr)
        if completed.returncode != 0:
            raise RuntimeError(f"k6 failed; inspect {directory / 'k6-console.txt'}")
        with raw_path.open("rb") as source, gzip.open(f"{raw_path}.gz", "wb") as target:
            shutil.copyfileobj(source, target)
        raw_path.unlink()
        summary: dict[str, Any] = json.loads(summary_path.read_text())
        return k6_metrics(summary)

    def run_cache_experiment(self, rate: int, duration: str) -> None:
        for enabled in (True, False):
            configuration = "enabled" if enabled else "disabled"
            for repetition in range(1, self.repetitions + 1):
                run_id = f"cache-{configuration}-r{repetition}"
                directory = self.output / "raw" / run_id
                resource_path = directory / "resources.jsonl"
                self.reset_state()
                self.configure_cache(enabled)
                self.seed_fleet_state()
                warm = self.client.get("/v1/fleet/state")
                warm.raise_for_status()
                self.redis("DEL", "fleetpulse:cache:stats")
                metrics = self.run_k6(
                    directory,
                    mode="read",
                    rate=rate,
                    duration=duration,
                    run_id=run_id,
                    resource_path=resource_path,
                )
                stats = self.client.get("/v1/cache/stats")
                stats.raise_for_status()
                cache = stats.json()
                hits = int(cache["hits"])
                misses = int(cache["misses"])
                total = hits + misses
                result: dict[str, Any] = {
                    "experiment": "cache",
                    "configuration": configuration,
                    "repetition": repetition,
                    "cache_enabled": enabled,
                    "cache_hits": hits,
                    "cache_misses": misses,
                    "cache_hit_rate": hits / total if total else 0,
                    **metrics,
                }
                self.finish_result(directory, result, resource_path)

    def queue_state(self) -> dict[str, int]:
        raw = self.redis("XINFO", "GROUPS", "fleetpulse:telemetry", check=False)
        if not raw or "no such key" in raw.lower():
            return {"pending": 0, "lag": 0, "backlog": 0}
        lines = raw.splitlines()
        values = dict(zip(lines[0::2], lines[1::2], strict=False))
        pending = int(values.get("pending", "0"))
        lag_value = values.get("lag", "0")
        lag = 0 if lag_value in {"", "NULL"} else int(lag_value)
        return {"pending": pending, "lag": lag, "backlog": pending + lag}

    def wait_for_worker_group(self) -> None:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            raw = self.redis("XINFO", "GROUPS", "fleetpulse:telemetry", check=False)
            if "fleetpulse-workers" in raw:
                return
            time.sleep(0.25)
        raise RuntimeError("worker consumer group did not appear")

    def wait_for_outbox(self) -> None:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self.psql("SELECT count(*) FROM outbox_events WHERE published_at IS NULL;") == "0":
                return
            time.sleep(0.1)
        raise RuntimeError("outbox relay did not publish the workload")

    def run_worker_experiment(self, rate: int, duration: str) -> None:
        self.configure_cache(True)
        for workers in (1, 4):
            for repetition in range(1, self.repetitions + 1):
                run_id = f"workers-{workers}-r{repetition}"
                directory = self.output / "raw" / run_id
                directory.mkdir(parents=True)
                resource_path = directory / "resources.jsonl"
                queue_path = directory / "queue.jsonl"
                self.reset_state()
                self.compose("up", "-d", "--scale", f"worker={workers}", "worker")
                self.wait_for_worker_group()
                self.compose("pause", "worker")
                self.compose("up", "-d", "outbox-relay")
                metrics = self.run_k6(
                    directory,
                    mode="ingest",
                    rate=rate,
                    duration=duration,
                    run_id=run_id,
                    resource_path=resource_path,
                )
                self.wait_for_outbox()
                self.compose("pause", "outbox-relay")
                initial = self.queue_state()
                accepted = int(self.psql("SELECT count(*) FROM telemetry_batches;"))
                if initial["backlog"] != accepted:
                    raise RuntimeError(
                        f"backlog {initial['backlog']} did not match accepted events {accepted}"
                    )

                stop = threading.Event()
                sampler = threading.Thread(
                    target=self.sample_resources, args=(resource_path, stop), daemon=True
                )
                sampler.start()
                started = time.monotonic()
                self.compose("unpause", "worker")
                peak = initial["backlog"]
                deadline = started + 120
                processed = 0
                try:
                    while time.monotonic() < deadline:
                        state = self.queue_state()
                        processed = int(self.psql("SELECT count(*) FROM processed_events;"))
                        peak = max(peak, state["backlog"])
                        with queue_path.open("a") as stream:
                            stream.write(
                                json.dumps(
                                    {
                                        "sampled_at": utc_now(),
                                        "processed": processed,
                                        **state,
                                    },
                                    sort_keys=True,
                                )
                                + "\n"
                            )
                        if state["backlog"] == 0 and processed == accepted:
                            break
                        time.sleep(0.1)
                    else:
                        raise RuntimeError("worker backlog did not drain before timeout")
                finally:
                    stop.set()
                    sampler.join(timeout=10)
                drained = time.monotonic() - started
                result = {
                    "experiment": "workers",
                    "configuration": str(workers),
                    "repetition": repetition,
                    "worker_count": workers,
                    "accepted_events": accepted,
                    "processed_events": processed,
                    "initial_backlog": initial["backlog"],
                    "peak_backlog": peak,
                    "drain_seconds": drained,
                    "worker_throughput_eps": accepted / drained,
                    **metrics,
                }
                self.finish_result(directory, result, resource_path)
                self.compose("stop", "worker", "outbox-relay", check=False)

    def finish_result(self, directory: Path, result: dict[str, Any], resource_path: Path) -> None:
        from fleetpulse_project.performance import resource_metrics

        resources = resource_metrics(resource_path)
        result["resources"] = resources
        for service, values in resources.items():
            result[f"resource_{service}_cpu_max_percent"] = values["cpu_max_percent"]
            result[f"resource_{service}_memory_max_bytes"] = values["memory_max_bytes"]
        write_json(directory / "result.json", result)
        self.results.append(result)
        write_json(self.output / "results.json", self.results)

    def metadata(
        self,
        profile: str,
        cache_rate: int,
        cache_duration: str,
        worker_rate: int,
        worker_duration: str,
    ) -> dict[str, Any]:
        def output(arguments: list[str]) -> str:
            return self.command(arguments).stdout.strip()

        return {
            "recorded_at": utc_now(),
            "profile": profile,
            "repetitions": self.repetitions,
            "repository": str(ROOT),
            "compose_project": self.project_name,
            "git_commit": output(["git", "rev-parse", "HEAD"]),
            "git_worktree_dirty": bool(output(["git", "status", "--porcelain"])),
            "host": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "logical_cpus": os.cpu_count(),
            },
            "docker": {
                "version": output(["docker", "version", "--format", "{{.Server.Version}}"]),
                "cpus": int(output(["docker", "info", "--format", "{{.NCPU}}"])),
                "memory_bytes": int(output(["docker", "info", "--format", "{{.MemTotal}}"])),
            },
            "k6_version": output(["k6", "version"]),
            "workloads": {
                "cache_read_rate_rps": cache_rate,
                "cache_duration": cache_duration,
                "cache_seeded_records": 1,
                "worker_ingest_rate_rps": worker_rate,
                "worker_duration": worker_duration,
                "api_replicas": 2,
                "worker_counts": [1, 4],
                "arrival_model": "constant-arrival-rate",
            },
            "security": {
                "credentials": "ephemeral and excluded from artifacts",
                "ingress": "loopback TLS via Nginx",
                "k6_tls_verification": "disabled only for generated local CA benchmark traffic",
            },
        }

    def finalize(self, metadata: dict[str, Any]) -> None:
        aggregate = aggregate_results(self.results)
        write_json(self.output / "aggregate.json", aggregate)
        write_json(self.output / "metadata.json", metadata)
        lines = [
            "# Phase 6 performance and capacity evidence",
            "",
            "All numbers in the measured tables are local measurements from the recorded "
            "commit and",
            "machine in `metadata.json`. They are not claims of production or cloud scale.",
            "",
            "## Measured cache comparison",
            "",
            "| Cache | Repetitions | Throughput (req/s) | p50 (ms) | p95 (ms) | "
            "p99 (ms) | Error rate | Hit rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for configuration in ("enabled", "disabled"):
            values = aggregate[f"cache:{configuration}"]
            lines.append(
                f"| {configuration} | {values['repetitions']:.0f} | "
                f"{values['throughput_rps']:.2f} | {values['p50_ms']:.2f} | "
                f"{values['p95_ms']:.2f} | {values['p99_ms']:.2f} | "
                f"{values['error_rate']:.4f} | {values.get('cache_hit_rate', 0):.4f} |"
            )
        lines.extend(
            [
                "",
                "## Measured worker comparison",
                "",
                "| Workers | Repetitions | Accepted | Initial backlog | Drain (s) | "
                "Processing (events/s) | Ingest p95 (ms) | Errors |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for configuration in ("1", "4"):
            values = aggregate[f"workers:{configuration}"]
            lines.append(
                f"| {configuration} | {values['repetitions']:.0f} | "
                f"{values['accepted_events']:.0f} | {values['initial_backlog']:.0f} | "
                f"{values['drain_seconds']:.3f} | {values['worker_throughput_eps']:.2f} | "
                f"{values['p95_ms']:.2f} | {values['error_rate']:.4f} |"
            )
        lines.extend(
            [
                "",
                "## Measured resource envelope",
                "",
                "CPU is the maximum aggregate Docker CPU percentage for all containers of "
                "the service. Memory is the maximum aggregate resident allocation reported "
                "by Docker.",
                "",
                "| Experiment | Configuration | API max CPU | API max memory (MiB) | "
                "Worker max CPU | Worker max memory (MiB) |",
                "| --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for experiment, configuration in (
            ("cache", "enabled"),
            ("cache", "disabled"),
            ("workers", "1"),
            ("workers", "4"),
        ):
            values = aggregate[f"{experiment}:{configuration}"]
            api_cpu = values.get("resource_api_cpu_max_percent", 0)
            api_memory = values.get("resource_api_memory_max_bytes", 0) / 1024**2
            worker_cpu = values.get("resource_worker_cpu_max_percent", 0)
            worker_memory = values.get("resource_worker_memory_max_bytes", 0) / 1024**2
            lines.append(
                f"| {experiment} | {configuration} | {api_cpu:.2f}% | {api_memory:.2f} | "
                f"{worker_cpu:.2f}% | {worker_memory:.2f} |"
            )
        lines.extend(
            [
                "",
                "## Evidence-based planning projections",
                "",
                "The following values are projections, not measurements. They apply a 30% "
                "operating",
                "headroom to the median measured queue-drain rate, then translate the result "
                "into daily",
                "events and agents reporting once per minute. They assume this workload and "
                "local machine;",
                "they do not assume linear scaling beyond a tested configuration.",
                "",
                "| Tested workers | Projected planning rate (events/s) | Projected events/day | "
                "Projected 60s agents |",
                "| ---: | ---: | ---: | ---: |",
            ]
        )
        for configuration in ("1", "4"):
            measured = aggregate[f"workers:{configuration}"]["worker_throughput_eps"]
            planning = measured * 0.70
            lines.append(
                f"| {configuration} | {planning:.2f} | {planning * 86400:.0f} | "
                f"{planning * 60:.0f} |"
            )
        lines.extend(
            [
                "",
                "## Interpretation limits",
                "",
                "- The constant-arrival workload proves behavior only at the tested rates; it is "
                "not a saturation test.",
                "- Docker Desktop CPU and memory samples are local observations and include "
                "virtualization effects.",
                "- Cache and worker axes are isolated experiments; the report does not infer a "
                "Cartesian interaction.",
                "- Alert detection and incident recovery time are intentionally not measured "
                "here; Phase 7 owns those drills.",
                "- Raw k6 samples, per-run summaries, resource samples, and queue samples are "
                "retained under `raw/`.",
                "",
            ]
        )
        (self.output / "capacity-plan.md").write_text("\n".join(lines))

    def close(self) -> None:
        self.client.close()
        if not self.keep_running:
            self.compose("down", "--volumes", check=False)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("smoke", "full"), default="full")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--keep-running", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    profile = str(arguments.profile)
    if profile == "smoke":
        repetitions, cache_rate, cache_duration, worker_rate, worker_duration = (
            1,
            10,
            "3s",
            10,
            "3s",
        )
    else:
        repetitions, cache_rate, cache_duration, worker_rate, worker_duration = (
            3,
            100,
            "20s",
            50,
            "10s",
        )
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = arguments.output or ROOT / "evidence/runs" / f"{timestamp}-phase-6"
    harness = PerformanceHarness(output.resolve(), repetitions, bool(arguments.keep_running))
    try:
        harness.setup()
        metadata = harness.metadata(
            profile, cache_rate, cache_duration, worker_rate, worker_duration
        )
        harness.run_cache_experiment(cache_rate, cache_duration)
        harness.run_worker_experiment(worker_rate, worker_duration)
        harness.finalize(metadata)
    finally:
        harness.close()
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
