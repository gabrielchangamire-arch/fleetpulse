# Assistant v1 verification — 2026-10-07

Measured locally on Python 3.13.14; offline only. Original baseline: `make verify` passed with
32 tests. Updated `make verify`: **65 tests passed**, Ruff lint/format and strict mypy passed,
repository contract, legacy 5-case assistant regression, CI contract and evidence audit passed.
One existing Starlette/httpx deprecation warning remains; it did not fail tests.

The browser demo was exercised on loopback: selected disk-full, requested offline analysis,
and observed the source record beside its exact excerpt, offline label and unavailable token/cost
values. API tests also cover the demo catalog and rejection of cross-origin analysis.

Both versioned offline splits ran (16 cases each), using dataset v1.0.1:

| Measurement | Development | Held-out |
| --- | --- | --- |
| Application boundary expectations | 16/16 | 16/16 |
| Fixture-labeled diagnosis correctness | 15/16 | 14/16 |
| Fixture-labeled claim support | 11/12 returned claims | 11/12 returned claims |
| Citation validity / excerpt matches | 12/12 each | 12/12 each |
| Appropriate abstention | 15/16 | 14/16 |
| Synthetic redaction failures | 0 | 0 |

The intentional irrelevant-citation case passes mechanical validation and fails semantic grading.
These percentages describe scripted fixtures, **not model accuracy**. Full per-case results,
denominators and dataset hashes are in `offline-development.json` and `offline-held-out.json`.
No live-model request was made; token usage and estimated cost are unavailable. To run live tests,
provide a backend API key, available model, approved request budget and optional current USD rates.

The existing fleet stack, container scans and load/drill suites were not rerun for this isolated
assistant change. The branch preserves earlier evidence without presenting it as a new measurement.

## CI follow-up

The first draft-branch CI run passed Python quality, dependency audit, full-history secret scan,
manifest security and Compose ingestion smoke. Image security failed: the existing pinned base
contained 50 fixable HIGH/CRITICAL findings per image, repeated across five images. The official
Python 3.13 slim index was refreshed to the registry-verified digest
`sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c`
(Python 3.13.16, published 2026-10-06). The gate and finding thresholds are unchanged.

The refreshed base eliminated the OS findings. The next scan identified pip's bundled dependencies
(msgpack, urllib3 and setuptools metadata). Pip and its actual bundled ensurepip wheel are removed
after installation in all five runtime images; application dependencies remain hash-locked. This
removes build-only package installation from the runtime rather than suppressing scan findings.

Dataset v1.0.1 separates task abstention labels from the expected handling of deliberately faulty
provider output. An answerable incident rejected for an invalid provider citation passes the safety
regression but does not count as a correct diagnosis or appropriate task-level abstention. This
label correction and question clarification happened before any live model evaluation.

A local rebuilt assistant container passed offline analysis, packaged static-asset availability,
and absence of pip/ensurepip checks after removing the installers.
