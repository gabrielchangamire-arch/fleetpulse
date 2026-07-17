# Phase 6 smoke attempt: parser compatibility failure

The isolated Compose environment started successfully and the cache-enabled k6 workload
completed with 31 requests, zero failed checks, and zero HTTP failures. The runner then stopped
because k6 2.1 exports metric fields directly while its parser expected the older nested
`values` object. The valid raw samples, summary, console report, and resource samples are
preserved under `raw/cache-enabled-r1/`.

The parser was updated and unit-tested against both summary formats before the next run.
