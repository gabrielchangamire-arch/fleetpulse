"""Queue contract tests."""

import pytest
from pydantic import ValidationError

from fleetpulse.worker.main import decode_event


def test_decode_event_rejects_poison_payload() -> None:
    with pytest.raises((ValidationError, KeyError)):
        decode_event({"event_id": "not-a-uuid"})


def test_decode_event_accepts_relay_shape() -> None:
    event = decode_event(
        {
            "event_id": "00000000-0000-4000-8000-000000000010",
            "event_type": "telemetry.batch.accepted.v1",
            "aggregate_id": "00000000-0000-4000-8000-000000000011",
            "payload": '{"agent_id":"agent","batch_id":"batch"}',
        }
    )
    assert event.payload["agent_id"] == "agent"
