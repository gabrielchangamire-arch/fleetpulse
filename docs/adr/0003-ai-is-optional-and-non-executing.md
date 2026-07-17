# ADR 0003: AI is optional and non-executing

- Status: Accepted
- Date: 2026-07-17

## Context

Incident analysis may benefit from an AI assistant, but fleet reliability and system safety cannot depend on model availability or unconstrained output.

## Decision

The assistant is disabled by default and isolated from operational credentials and tools. The API supplies curated, redacted evidence identifiers. Responses require citations to supplied evidence or explicit abstention. Remediation text is a proposal only. Human approval may be recorded but never triggers execution.

## Consequences

Core operations continue when the assistant is absent. Accuracy, redaction, citation completeness, and abstention require dedicated evaluation.

