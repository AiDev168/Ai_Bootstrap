# ADR-004: Doctor-Planner-Executor Pipeline

- **Status:** Accepted
- **Date:** 2026-08-08

## Context

The project has evolved from a read-only environment audit into a controlled
diagnostic, planning, and remediation platform.

Doctor provides deterministic environment diagnostics and Planner now converts those
diagnostics into an `ExecutionPlan`.

A stable architectural boundary is required before system-changing behavior is added.

## Decision

The canonical application pipeline is:

```text
Probe
  ↓
Doctor / AuditService
  ↓
AuditReport
  ↓
Planner
  ↓
ExecutionPlan
  ↓
Executor
  ↓
Application / CLI / GUI
```

Responsibilities are strictly separated:

- Probe observes.
- Doctor diagnoses and reports.
- Planner creates the execution plan.
- Executor performs approved system changes.
- CLI and GUI present/orchestrate through application services.

Only Executor may perform system-changing operations.

## Public Model Boundary

Planner consumes public Doctor models.

Executor consumes public Planner models.

Upper layers must not bypass these contracts or inspect lower-layer implementation
details when a public model is available.

## Current Planner Contract

Planner Foundation provides:

- `ExecutionPlan`;
- `ExecutionPlanAction`;
- stable action identifiers;
- priority;
- deterministic ordering;
- duplicate-action elimination;
- safe handling of unknown checks.

Planner remains read-only.

## Executor Boundary

Executor is the only write-capable layer.

The Executor Foundation must establish the public execution contract before adding a
large remediation catalog.

Execution actions must be:

- explicit;
- controlled;
- observable;
- testable;
- limited to the approved execution plan.

Doctor and Planner must remain read-only.

## GUI

The professional GUI is the primary long-term user interface.

CLI remains important for:

- automation;
- CI/CD;
- diagnostics;
- testing;
- developer workflows.

Both interfaces must use the same core/application services.

## Consequences

The architecture provides a clear path from diagnosis to controlled remediation and
prevents remediation logic from leaking into Doctor, Planner, CLI, or GUI.

Future changes to this pipeline require a new or superseding ADR.
