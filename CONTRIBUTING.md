# Contributing

## Change discipline

1. Work on one roadmap phase at a time.
2. Add or update tests with behavior changes.
3. Run `make verify` before committing; use `make final-gate` for dependency, manifest, image, or
   CI changes.
4. Preserve raw test and measurement output needed to reproduce claims.
5. Document failure modes and operational changes in the relevant ADR or runbook.

## Reliability requirements

Network and queue interactions require explicit timeouts. Retried operations require bounded exponential backoff with jitter and an idempotency strategy. Long-running processes must handle termination gracefully. Permanently failing asynchronous work must be inspectable through dead-letter handling.

## Evidence language

- **Measured:** observed in a preserved run with metadata and raw output.
- **Projected:** derived from measurements using documented assumptions.
- **Target:** a desired objective that has not necessarily been achieved.

Never present a target or projection as a measured result.

## Dependency and image updates

Run `make lock` after changing Python dependency bounds. Review both hashed lock files rather than
editing generated versions manually. Runtime and scanner image changes must update the tag and
multi-platform digest together, pass the CI contract, regenerate SBOMs, and disclose any remaining
unfixed vulnerability findings.
