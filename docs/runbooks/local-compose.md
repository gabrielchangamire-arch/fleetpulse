# Local Compose runbook

## Purpose

Start and verify the Phase 1 agent-to-PostgreSQL vertical slice without cloud resources. Only the API binds a host port, and it binds to loopback. PostgreSQL remains on the private Compose data network.

## Prerequisites

- Docker Desktop or a compatible Docker Engine with Compose
- Python 3.11 or later

## Configure

Copy `.env.example` to the ignored `.env`. Replace both placeholders with independently generated local values. Never commit `.env`.

## Start and verify

```bash
make bootstrap
make compose-up
make phase1-smoke
docker compose ps
```

Expected smoke output reports a passed authentication boundary, one durable batch, and a duplicate replay. The continuously running agent appears separately in `/v1/fleet/agents`.

## Inspect

```bash
docker compose logs --tail=100 api agent
docker compose exec postgres psql -U fleetpulse -d fleetpulse
```

Agent and API logs are JSON and share batch/request correlation IDs. PostgreSQL is intentionally accessed through `docker compose exec`, not a published database port.

## Stop safely

```bash
docker compose stop agent api postgres
```

Stopping the agent sends `SIGTERM`; it flushes an incomplete batch to its durable spool before exiting. Named volumes preserve PostgreSQL and spool state.

## Destructive reset

The following command permanently deletes only FleetPulse Compose volumes and all local telemetry. Use it only when a clean disposable environment is intended:

```bash
docker compose down --volumes
```

