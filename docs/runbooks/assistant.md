# Read-only incident assistant runbook

## Offline local demo

The default provider is deterministic and does not call an external AI service:

```bash
make assistant-eval
make assistant-up
curl -sS http://127.0.0.1:8081/readyz
```

Submit only the evidence needed for the question:

```bash
curl -sS http://127.0.0.1:8081/v1/analysis \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: operator-demo-1' \
  -d '{"question":"What is supported?","evidence":[{"source":"alert","content":"API error alert fired."}]}'
```

Reviewing a proposal requires its returned `analysis_id` and `proposal_id`. A successful review
returns `execution_available: false`; it never changes FleetPulse or the host.

## Optional OpenAI provider

Use an ignored local `.env` or exported environment variable. Never paste a key into a command,
log, evidence file, issue, or committed configuration.

```bash
export FLEETPULSE_ASSISTANT_PROVIDER=openai
export FLEETPULSE_ASSISTANT_API_KEY='your-local-key'
export FLEETPULSE_ASSISTANT_MODEL='your-approved-model'
docker compose --profile ai up -d --build --wait assistant
```

The container receives no database, Redis, agent, Kubernetes, shell, or deployment credential.
Stop the optional slice with `docker compose --profile ai stop assistant`.

## Failure behavior

- Missing key with `provider=openai`: startup fails closed.
- Timeout, rate limit after bounded retries, malformed output, or invalid citation: the request
  returns an abstention and no remediation proposal.
- Model/provider unavailable: ingestion, queue processing, alerting, and incident state continue
  unchanged because they do not depend on this service.

The deterministic golden set validates the application safety contract. A live model evaluation
would be separate evidence and must identify the exact model, prompt, date, and dataset.
