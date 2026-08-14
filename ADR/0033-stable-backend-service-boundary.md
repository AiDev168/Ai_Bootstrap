# ADR-033: Stable Backend Service Boundary

## Status

Accepted for Step 31.

## Context

The backend HTTP layer must remain a presentation boundary. It must not own
reconciliation, planning, approval, execution, or session business rules.

The existing application already provides the canonical bootstrap workflow and
thread-safe session repository. Step 31 requires one application service boundary
that composes those public contracts without duplicating business logic.

## Decision

Introduce an application-level `EnvironmentSessionService` and keep
`ApplicationBackend` as the stable facade consumed by CLI/GUI transports.

The boundary is:

```text
HTTP / CLI / GUI
      ↓
ApplicationBackend
      ↓
EnvironmentSessionService
      ↓
Audit / Reconciliation / StrategyPlanner / ExecutionPlanBuilder
      ↓
EnvironmentBootstrapService
      ↓
Pipeline → Validation → SafetyGate → Approval → Executor → Verification
```

Session state is stored through the `SessionRepository` abstraction. The backend
must not manipulate repository internals or duplicate reconciliation logic.

Validated strategy decisions are converted to `ExecutionPlan` only through the
existing executor capability registry. Unknown strategy-to-action mappings fail
closed.

## Execution

A session may be created, inspected, planned, approved/rejected/skipped, started,
and cancelled through the application service. REAL execution requires all required
human approvals before the canonical bootstrap pipeline is invoked.

`EnvironmentBootstrapService` accepts an optional `plan_override` so a previously
reviewed session plan can be executed without regenerating a different plan in the
presentation layer.

## Consequences

Positive:

- GUI and CLI share one application boundary.
- Session lifecycle becomes testable without HTTP.
- Approved plans execute through the existing safety architecture.
- LLM decisions remain decision-only and are recorded as session evidence.
- Unknown mappings fail closed.

Negative:

- The service layer becomes an additional application abstraction that must remain
  small and explicit.
- Durable session persistence remains a later concern.

## Invariants

- HTTP handlers contain no remediation business logic.
- Executor remains the only write-capable layer.
- LLM output never becomes executable without validation and capability binding.
- Session approval is bound to a concrete action in the persisted plan.
