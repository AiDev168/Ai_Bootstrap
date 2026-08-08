# Bootstrap Process

## Product Workflow

The bootstrap process is a controlled environment workflow, not merely a checklist.

The target workflow is:

```text
Inspect
  ↓
Doctor
  ↓
Plan
  ↓
Review / Approve
  ↓
Execute
  ↓
Verify
```

## Stage 1 — Inspect

Read-only probes inspect:

- operating system;
- Python;
- virtual environment;
- installed dependencies;
- Git;
- Docker;
- platform;
- runtime target;
- best-effort GPU state.

No changes are performed.

## Stage 2 — Doctor

Doctor aggregates the inspection results into an `AuditReport`.

It provides:

- check status;
- categories;
- readiness;
- Health Score;
- context-aware recommendations;
- deterministic JSON for automation.

Doctor does not fix anything.

## Stage 3 — Plan

Planner converts the `AuditReport` into an `ExecutionPlan`.

Planner:

- maps known failures to actions;
- assigns stable action IDs;
- assigns priorities;
- removes duplicate actions;
- preserves deterministic ordering;
- safely ignores unknown failures.

Planner remains read-only.

## Stage 4 — Review / Approval

The execution plan must be visible before system-changing operations.

The professional GUI is the preferred long-term interface for review and approval.

CLI remains useful for diagnostics and automation.

## Stage 5 — Execute

Executor is the only component allowed to modify the environment.

Execution must be:

- explicit;
- controlled;
- observable;
- testable;
- limited to approved actions.

The current `bootstrap` command does not yet execute changes.

## Stage 6 — Verify

After execution, run Doctor again.

The intended remediation loop is:

```text
Doctor(before)
    ↓
Planner
    ↓
User approval
    ↓
Executor
    ↓
Doctor(after)
```

This verifies that the requested environment state was actually achieved.

## Long-Term Command

The target CLI workflow is:

```bash
ai-bootstrap bootstrap
```

The target GUI workflow should provide the same core process with a richer interactive
experience.

## Safety Rule

No installation, configuration, or other host modification belongs in Probe,
Doctor, Planner, CLI, or GUI business logic.

Only Executor may perform system changes.
