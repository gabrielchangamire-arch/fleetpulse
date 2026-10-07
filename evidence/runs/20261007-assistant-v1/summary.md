# Assistant v1 verification — 2026-10-07

Measured locally on Python 3.13.14; offline only. Original baseline: `make verify` passed with
32 tests. Updated `make verify`: **65 tests passed**, Ruff lint/format and strict mypy passed,
repository contract, legacy 5-case assistant regression, CI contract and evidence audit passed.
One existing Starlette/httpx deprecation warning remains; it did not fail tests.

The browser demo was exercised on loopback: selected disk-full, requested offline analysis,
and observed the source record beside its exact excerpt, offline label and unavailable token/cost
values. API tests also cover the demo catalog and rejection of cross-origin analysis.

Both versioned offline splits ran (16 cases each). Each split reported:

| Measurement | Actual result |
| --- | --- |
| Application boundary expectations | 16/16 |
| Fixture-labeled diagnosis correctness | 15/16 |
| Fixture-labeled claim support | 11/12 returned claims |
| Citation validity / excerpt matches | 12/12 each |
| Appropriate abstention | 15/16 |
| Synthetic redaction failures | 0 |

The intentional irrelevant-citation case passes mechanical validation and fails semantic grading.
These percentages describe scripted fixtures, **not model accuracy**. Full per-case results,
denominators and dataset hashes are in `offline-development.json` and `offline-held-out.json`.
No live-model request was made; token usage and estimated cost are unavailable. To run live tests,
provide a backend API key, available model, approved request budget and optional current USD rates.

The existing fleet stack, container scans and load/drill suites were not rerun for this isolated
assistant change. The branch preserves earlier evidence without presenting it as a new measurement.
