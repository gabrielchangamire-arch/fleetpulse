"""Unit tests for Phase 6 evidence parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fleetpulse_project.performance import (
    aggregate_results,
    k6_metrics,
    parse_bytes,
    parse_percent,
    resource_metrics,
)


def test_parse_docker_values() -> None:
    assert parse_percent("12.50%") == 12.5
    assert parse_bytes("1KiB") == 1024
    assert parse_bytes("12.5 MiB") == 13_107_200
    assert parse_bytes("1GB") == 1_000_000_000
    with pytest.raises(ValueError, match="unsupported"):
        parse_bytes("12 blocks")


def test_extract_k6_summary_metrics() -> None:
    summary = {
        "metrics": {
            "http_req_duration": {
                "values": {"med": 4, "p(95)": 8, "p(99)": 10},
            },
            "http_reqs": {"values": {"count": 100, "rate": 20}},
            "http_req_failed": {"values": {"rate": 0.01}},
            "iterations": {"values": {"count": 99}},
        }
    }
    assert k6_metrics(summary) == {
        "requests": 100.0,
        "throughput_rps": 20.0,
        "iterations": 99.0,
        "p50_ms": 4.0,
        "p95_ms": 8.0,
        "p99_ms": 10.0,
        "error_rate": 0.01,
    }

    summary["metrics"] = {
        "http_req_duration": {"med": 4, "p(95)": 8, "p(99)": 10},
        "http_reqs": {"count": 100, "rate": 20},
        "http_req_failed": {"value": 0.01},
        "iterations": {"count": 99},
    }
    assert k6_metrics(summary)["error_rate"] == 0.01


def test_resource_and_repetition_aggregation(tmp_path: Path) -> None:
    samples = tmp_path / "resources.jsonl"
    samples.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "sample_id": 1,
                        "service": "api",
                        "cpu_percent": 10,
                        "memory_bytes": 100,
                    }
                ),
                json.dumps(
                    {
                        "sample_id": 2,
                        "service": "api",
                        "cpu_percent": 20,
                        "memory_bytes": 150,
                    }
                ),
            ]
        )
    )
    assert resource_metrics(samples)["api"] == {
        "cpu_median_percent": 15,
        "cpu_max_percent": 20,
        "memory_max_bytes": 150,
        "samples": 2,
    }

    aggregate = aggregate_results(
        [
            {
                "experiment": "cache",
                "configuration": "enabled",
                "requests": 10,
                "throughput_rps": 5,
                "p50_ms": 2,
                "p95_ms": 4,
                "p99_ms": 5,
                "error_rate": 0,
                "cache_hit_rate": 1,
            },
            {
                "experiment": "cache",
                "configuration": "enabled",
                "requests": 12,
                "throughput_rps": 7,
                "p50_ms": 3,
                "p95_ms": 6,
                "p99_ms": 8,
                "error_rate": 0.02,
                "cache_hit_rate": 0.98,
            },
        ]
    )
    assert aggregate["cache:enabled"]["throughput_rps"] == 6
    assert aggregate["cache:enabled"]["p95_ms"] == 5
    assert aggregate["cache:enabled"]["cache_hit_rate"] == 0.99
