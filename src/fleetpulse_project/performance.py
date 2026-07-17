"""Parse and aggregate reproducible FleetPulse performance evidence."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

BYTE_UNITS = {
    "B": 1,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "KIB": 1024,
    "MIB": 1024**2,
    "GIB": 1024**3,
}


def parse_percent(value: str) -> float:
    """Convert Docker's percentage strings to numeric percentages."""
    return float(value.strip().removesuffix("%"))


def parse_bytes(value: str) -> int:
    """Convert one Docker memory value such as ``12.4MiB`` to bytes."""
    compact = value.strip().upper().replace(" ", "")
    for unit in sorted(BYTE_UNITS, key=len, reverse=True):
        if compact.endswith(unit):
            number = compact[: -len(unit)]
            return round(float(number) * BYTE_UNITS[unit])
    raise ValueError(f"unsupported byte value: {value}")


def k6_metrics(summary: dict[str, Any]) -> dict[str, float]:
    """Extract metrics from both legacy and k6 2.x summary-export shapes."""
    metrics = summary["metrics"]
    duration = metrics["http_req_duration"]
    requests = metrics["http_reqs"]
    failures = metrics["http_req_failed"]
    iterations = metrics["iterations"]
    duration = duration.get("values", duration)
    requests = requests.get("values", requests)
    failures = failures.get("values", failures)
    iterations = iterations.get("values", iterations)
    return {
        "requests": float(requests["count"]),
        "throughput_rps": float(requests["rate"]),
        "iterations": float(iterations["count"]),
        "p50_ms": float(duration["med"]),
        "p95_ms": float(duration["p(95)"]),
        "p99_ms": float(duration["p(99)"]),
        "error_rate": float(failures["rate"] if "rate" in failures else failures["value"]),
    }


def resource_metrics(path: Path) -> dict[str, dict[str, float]]:
    """Summarize Docker stats samples by Compose service."""
    samples: dict[str, dict[int, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    if not path.exists():
        return {}
    for index, line in enumerate(path.read_text().splitlines()):
        if line.strip():
            record: dict[str, Any] = json.loads(line)
            sample_id = int(record.get("sample_id", index))
            samples[str(record["service"])][sample_id].append(record)
    result: dict[str, dict[str, float]] = {}
    for service, batches in sorted(samples.items()):
        cpu = [sum(float(item["cpu_percent"]) for item in records) for records in batches.values()]
        memory = [
            sum(float(item["memory_bytes"]) for item in records) for records in batches.values()
        ]
        result[service] = {
            "cpu_median_percent": statistics.median(cpu),
            "cpu_max_percent": max(cpu),
            "memory_max_bytes": max(memory),
            "samples": float(len(batches)),
        }
    return result


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Return medians for repeated measurements grouped by experiment/configuration."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        key = f"{result['experiment']}:{result['configuration']}"
        grouped[key].append(result)

    fields = {
        "requests",
        "throughput_rps",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "error_rate",
        "cache_hit_rate",
        "accepted_events",
        "worker_throughput_eps",
        "initial_backlog",
        "peak_backlog",
        "drain_seconds",
    }
    fields.update(
        key
        for result in results
        for key, value in result.items()
        if key.startswith("resource_") and isinstance(value, int | float)
    )
    aggregate: dict[str, dict[str, float]] = {}
    for key, records in sorted(grouped.items()):
        values: dict[str, float] = {"repetitions": float(len(records))}
        for field in sorted(fields):
            observed = [float(record[field]) for record in records if record.get(field) is not None]
            if observed:
                values[field] = statistics.median(observed)
        aggregate[key] = values
    return aggregate
