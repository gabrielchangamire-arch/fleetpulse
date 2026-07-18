# Threshold incident response

## Signal

`FleetPulseIncidentDetected` means a worker created a new high-CPU or high-memory incident
within the recent-event alert window. The alert is a notification edge, while PostgreSQL is the
durable incident record.

## Triage

1. Query `/v1/incidents` and capture the incident ID, agent, type, evidence batch, value, and
   threshold.
2. Use the evidence batch UUID and correlation ID to locate API, relay, and worker logs.
3. Check `fleetpulse_queue_pending` so queue delay is not mistaken for host detection delay.
4. Inspect recent deployment records before attributing cause.
5. Validate the affected host through an approved operator channel; telemetry alone is not
   authorization to change the host.

## Mitigation and recovery

FleetPulse does not execute remediation. An operator selects and approves any change using the
owning system's runbook. Keep the incident open until the host signal is below threshold and
fresh telemetry confirms recovery. Record detection, decision, mitigation, and validation
timestamps.

## Escalation

Escalate when multiple agents cross the same threshold, queue backlog delays current evidence,
the agent stops reporting, or the incident coincides with availability/ingestion SLO burn.
Never infer recovery solely because the recent-event Prometheus alert clears; it clears by
design after its notification window.
