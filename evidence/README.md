# Evidence policy

Evidence exists to support reproducibility and future portfolio statements without fabricating scale.

Each run directory uses `YYYYMMDDTHHMMSSZ-scenario-name` and contains:

- `metadata.json`: Git SHA, dirty state, UTC time, machine/runtime description, scenario, configuration, and commands.
- Raw test, load-generator, metrics, and log output.
- `summary.md`: measured results, failures, limitations, and links to raw files.
- Projection inputs and formulas when capacity projections are produced.

Every number is classified as **measured**, **projected**, or **target**. Raw sensitive data is redacted before preservation. Evidence files are committed when reasonably sized; large artifacts are compressed and indexed with a checksum and retention location.

