# Incident assistant interview walkthrough

1. Start at the request boundary in `models.py`: at most 50 bounded source records and a bounded
   question. The API gives each source a request-local ID and redacts common credentials before
   it reaches the provider. The assistant has no database, shell, deployment, or remediation tool.
2. Follow `OpenAIResponsesProvider.analyze`: strict JSON schema through `text.format`, no tools,
   `store=false`, an output-token cap, per-I/O timeout and overall deadline. Transient network,
   timeout, 408/409/429 and server errors retry with bounded jitter. Authentication, validation,
   quota exhaustion, refusals and malformed output fail without retry storms. A long Retry-After
   fails cleanly instead of violating either the server's requested delay or the local budget.
3. Provider output remains untrusted. Validate the schema, redact again, resolve citation IDs, and
   require each excerpt to be a literal substring of the cited redacted record. Claims and
   remediation rationales both carry excerpts. The public summary is assembled from those claims
   so an uncited provider summary cannot introduce a separate diagnosis.
4. Explain the limit with the `irrelevant-cite` scenario: “maintenance review next Friday” exists,
   but it does not support “disk is full.” The application cannot decide all semantic relationships
   deterministically. A valid excerpt is traceability, not truth. Separate fixture/human semantic
   grades expose this limitation. A live model should abstain when support is absent or conflicting.
5. Open the local interface. Inspect sources before requesting analysis; compare each claim with
   its quote. Offline mode echoes a record and demonstrates the UI and safety plumbing, not a
   diagnosis model. It may quote an injected instruction as source text but cannot execute it.
6. Show the 32-case evaluation, fixed development/held-out split, and intentional negative cases.
   The fixture suite demonstrates validation, not general model accuracy. A live run saves outputs,
   timing and usage; independent human grades are attached to exact output hashes afterward.
7. Discuss failure handling: any provider or grounding failure gives a safe abstention and no
   proposal. Typed metadata allows troubleshooting without storing provider bodies or keys.
   Review receipts retain the original bounded, process-local non-executing behavior.

## Tradeoffs and next steps

A direct HTTP adapter and small static page keep the architecture understandable. There is no
vector database: callers already supply the incident evidence. Regex redaction is a limited
backstop, not a general data-loss prevention system; use synthetic or reviewed data for live demos.
The API is a loopback-only local demo with no authentication; add authentication, request budgets,
rate limiting and durable audit storage before any multi-user hosting. Browser cross-origin
analysis is rejected. This does not make a public endpoint safe.

Exact excerpts are required for new provider outputs; clients providing old ID-only analysis
fixtures must add excerpts. Request shape, existing review routes and non-execution behavior remain.
Historical Phase 8 evidence is preserved. Its five fixtures were extended to the new output shape;
new results live separately and do not rewrite the historical measurements.

Official contract checked on 2026-10-07:
[Responses](https://developers.openai.com/api/reference/python/resources/responses),
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), and
[error handling](https://developers.openai.com/api/docs/guides/error-codes).
Contract checks use mocked HTTP responses; no successful live call is claimed.
