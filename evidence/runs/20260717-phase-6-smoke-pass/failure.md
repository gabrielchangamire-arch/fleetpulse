# Phase 6 smoke attempt: worker artifact directory failure

This attempt completed the cache-enabled and cache-disabled workloads and retained both result
sets. It stopped before worker load generation because the worker experiment pre-created its
artifact directory and the shared k6 function attempted to create the same directory again
without `exist_ok=True`.

The conflict was corrected before the next run. No FleetPulse service or external repository
was modified outside this attempt's isolated Compose project.
