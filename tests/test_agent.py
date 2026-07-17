"""Agent collection, backoff, and durable spool tests."""

from pathlib import Path

from fleetpulse.agent.client import full_jitter_delay
from fleetpulse.agent.collector import collect_sample
from fleetpulse.agent.spool import BatchSpool
from tests.test_telemetry import batch


def test_full_jitter_is_capped_and_injectable() -> None:
    midpoint = lambda low, high: (low + high) / 2  # noqa: E731
    assert full_jitter_delay(0, 2, 10, midpoint) == 1
    assert full_jitter_delay(4, 2, 10, midpoint) == 5


def test_spool_persists_failure_and_replay(tmp_path: Path) -> None:
    database_path = tmp_path / "spool.db"
    telemetry_batch = batch()
    spool = BatchSpool(database_path, max_batches=10, max_bytes=1_000_000)
    assert spool.enqueue(telemetry_batch) == 0
    pending = spool.next_ready(now=0)
    assert pending is not None
    assert pending.batch == telemetry_batch
    assert pending.attempts == 0
    spool.mark_failed(telemetry_batch.batch_id, "timeout", next_attempt_at=10)
    assert spool.next_ready(now=9) is None
    spool.close()

    reopened = BatchSpool(database_path, max_batches=10, max_bytes=1_000_000)
    pending = reopened.next_ready(now=10)
    assert pending is not None
    assert pending.attempts == 1
    reopened.mark_sent(telemetry_batch.batch_id)
    assert reopened.count() == 0
    reopened.close()


def test_spool_evicts_oldest_batch_at_bound(tmp_path: Path) -> None:
    spool = BatchSpool(tmp_path / "bounded.db", max_batches=1, max_bytes=1_000_000)
    first = batch()
    second = batch()
    assert spool.enqueue(first) == 0
    assert spool.enqueue(second) == 1
    assert spool.count() == 1
    pending = spool.next_ready()
    assert pending is not None
    assert pending.batch.batch_id == second.batch_id
    spool.close()


def test_real_collector_returns_bounded_non_sensitive_sample() -> None:
    collected = collect_sample()
    assert collected.memory.total_bytes > 0
    assert collected.disks
    assert len(collected.top_processes) <= 10
    serialized = collected.model_dump_json()
    assert "cmdline" not in serialized
    assert "environ" not in serialized
