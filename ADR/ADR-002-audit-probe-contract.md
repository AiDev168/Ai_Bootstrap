# ADR-002: Audit Probe Contract and Reporting Semantics

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

Missing executables, unsupported platforms, timeouts, malformed version output, and individual probe errors are expected audit conditions. The environment audit must remain read-only and useful even when one check cannot complete.

## Decision

Each audit probe implements `run() -> AuditCheck`. A check has one of four statuses: `available`, `not_found`, `unsupported`, or `error`; it also carries normalized facts and an optional diagnostic. The aggregate audit continues after individual probe failures and returns a complete typed report.

Probes use safe subprocess argument arrays, timeouts, and captured output without a shell. They must not install, configure, start, stop, or otherwise modify host software. OS and Python facts come from the running process and standard-library platform APIs; Git, Docker, and best-effort GPU checks remain isolated adapters.

## Alternatives

- Aborting the audit with exceptions was rejected because one expected failure would hide unrelated results.
- Unstructured dictionaries and strings were rejected because they would make reporting and tests unstable.

## Consequences

Audit output and tests gain predictable semantics, while the four-value status vocabulary becomes part of the core data model. Vendor- and platform-specific GPU limitations are represented through status and diagnostics rather than treated as fatal failures. Human-readable tables are the default; deterministic JSON is supported for automation.
