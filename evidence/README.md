# Evidence policy

Evidence exists to support reproducibility and future portfolio statements without fabricating scale.

Each run directory uses `YYYYMMDDTHHMMSSZ-scenario-name` and contains:

- `metadata.json`: Git SHA, dirty state, UTC time, machine/runtime description, scenario, configuration, and commands.
- Raw test, load-generator, metrics, and log output.
- `summary.md`: measured results, failures, limitations, and links to raw files.
- Projection inputs and formulas when capacity projections are produced.

Every number is classified as **measured**, **projected**, or **target**. Raw sensitive data is redacted before preservation. Evidence files are committed when reasonably sized; large artifacts are compressed and indexed with a checksum and retention location.

Phase summaries:

- [Phase 6 performance and capacity](runs/20260717-phase-6/summary.md)
- [Phase 7 failure detection and recovery](runs/20260717-phase-7/summary.md)
- [Phase 8 assistant safety contract](runs/20260717-phase-8/summary.md)
