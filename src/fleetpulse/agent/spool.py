"""Bounded SQLite spool that preserves stable batches across agent restarts."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fleetpulse.telemetry import TelemetryBatch


@dataclass(frozen=True)
class PendingBatch:
    """A batch ready for a delivery attempt."""

    batch: TelemetryBatch
    attempts: int


class BatchSpool:
    """Durable FIFO spool bounded by batch count and serialized payload bytes."""

    def __init__(self, path: Path, max_batches: int, max_bytes: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._max_batches = max_batches
        self._max_bytes = max_bytes
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS batches (
                batch_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                payload_bytes INTEGER NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at REAL NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        self._connection.commit()

    def enqueue(self, batch: TelemetryBatch) -> int:
        """Persist a batch and evict oldest entries when the configured bound is exceeded."""
        payload = batch.model_dump_json()
        self._connection.execute(
            """
            INSERT OR IGNORE INTO batches
                (batch_id, payload, payload_bytes, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (str(batch.batch_id), payload, len(payload.encode()), time.time()),
        )
        dropped = 0
        while self.count() > self._max_batches or self.total_bytes() > self._max_bytes:
            cursor = self._connection.execute(
                """
                DELETE FROM batches
                WHERE batch_id = (
                    SELECT batch_id FROM batches ORDER BY created_at LIMIT 1
                )
                """
            )
            dropped += cursor.rowcount
        self._connection.commit()
        return dropped

    def next_ready(self, now: float | None = None) -> PendingBatch | None:
        """Return the oldest batch whose retry delay has elapsed."""
        timestamp = time.time() if now is None else now
        row = self._connection.execute(
            """
            SELECT payload, attempts FROM batches
            WHERE next_attempt_at <= ? ORDER BY created_at LIMIT 1
            """,
            (timestamp,),
        ).fetchone()
        if row is None:
            return None
        return PendingBatch(batch=TelemetryBatch.model_validate_json(row[0]), attempts=int(row[1]))

    def mark_sent(self, batch_id: UUID) -> None:
        self._connection.execute("DELETE FROM batches WHERE batch_id = ?", (str(batch_id),))
        self._connection.commit()

    def mark_failed(self, batch_id: UUID, error: str, next_attempt_at: float) -> None:
        self._connection.execute(
            """
            UPDATE batches
            SET attempts = attempts + 1, next_attempt_at = ?, last_error = ?
            WHERE batch_id = ?
            """,
            (next_attempt_at, error[:1000], str(batch_id)),
        )
        self._connection.commit()

    def count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) FROM batches").fetchone()
        return int(row[0]) if row else 0

    def total_bytes(self) -> int:
        row = self._connection.execute(
            "SELECT COALESCE(SUM(payload_bytes), 0) FROM batches"
        ).fetchone()
        return int(row[0]) if row else 0

    def close(self) -> None:
        self._connection.close()
