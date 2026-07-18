# Security policy

FleetPulse is a demonstration system and must default to local-only exposure.

## Secrets

- Commit templates and secret references, never live credentials, tokens, private keys, or generated certificates.
- Keep local secrets in ignored files or runtime secret stores.
- Use distinct application and read-only database roles.
- Redact credentials, authorization headers, cookies, connection strings, private keys, and common token formats from logs and AI context.

## Service exposure

Nginx is the only application ingress. PostgreSQL and Redis remain on private container or cluster networks. Prometheus and Grafana are reachable only through loopback bindings or Kubernetes port-forwarding. Kubernetes services default to `ClusterIP` and NetworkPolicies restrict east-west traffic.

## AI boundary

The optional assistant receives curated, redacted evidence. It has no shell, Kubernetes, cloud, deployment, or remediation tool. It may return a cited proposal; a human may record approval, but approval does not create an execution path.

## Supply chain

GitHub Actions use commit SHAs; container references use OCI digests; Python dependencies use
hashed lock files. CI retains CycloneDX SBOMs and complete Trivy reports for every application
image. A green gate means no reported HIGH/CRITICAL finding had an available upstream fix at scan
time—it does not mean the scanner reported zero inherited risk. Review the full artifact and the
risk register.

## Reporting

Do not open a public issue containing an exploit or secret. Record a sanitized reproduction and remediation in the repository's security documentation.
