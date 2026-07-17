# Repository and environment boundary

The FleetPulse Git root is `/Users/gabriel/Projects/fleetpulse` on the initial development machine.

The pre-existing `/Users/gabriel/Documents/Fleet-Pulse` Git repository is explicitly out of scope. FleetPulse scripts, Compose files, Kubernetes manifests, CI workflows, and documentation must not reference, mount, deploy, restart, or modify that repository or any Nemo/Oracle VM resource.

Every local phase gate captures the out-of-scope repository's porcelain Git status before and after work. A difference fails the isolation gate and must be investigated before proceeding.

Cloud resources are not part of the default architecture. Any future cloud overlay must be opt-in, separately documented, and unable to run from ordinary local targets.

