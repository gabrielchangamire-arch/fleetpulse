# Phase 6 smoke attempt: startup failure

This attempt stopped before any workload ran. The harness generated a fresh PostgreSQL
credential while Compose reused an existing FleetPulse volume initialized with a credential
from an earlier phase. PostgreSQL correctly rejected the mismatch, both API replicas remained
unhealthy, and the harness shut down the Compose services.

The harness was changed to use a unique Compose project and benchmark-owned volumes for every
run, then delete only those temporary volumes during cleanup. This preserves repository and
project isolation while making the experiment independent of prior local Compose state.
