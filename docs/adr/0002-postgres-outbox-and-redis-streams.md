# ADR 0002: PostgreSQL outbox with Redis Streams

- Status: Accepted
- Date: 2026-07-17

## Context

Redis is required for task queues and coordination, but an acknowledged ingestion batch must survive Redis restarts or loss.

## Decision

The API commits telemetry, idempotency state, and a transactional outbox row together in PostgreSQL. A relay publishes outbox work to a Redis Stream. Workers use consumer groups, idempotent database transitions, pending-message reclaim, bounded retry, and a dead-letter stream.

## Consequences

Redis outages delay processing rather than lose acknowledged work. The design adds relay and outbox cleanup complexity, which must be monitored and tested.

