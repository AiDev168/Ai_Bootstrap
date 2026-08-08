# AI Engineering Bootstrap — AI Coding Rules

## Mandatory Startup Procedure

Before making any change, read these documents in order:

1. `AGENTS.md`
2. `docs/CONSTITUTION.md`
3. relevant accepted ADRs
4. `IMPLEMENTATION_WORKFLOW.md`
5. `docs/PROJECT_CONTEXT.md`
6. `docs/architecture.md`
7. relevant source code and tests

These rules have higher priority than a feature prompt.

If a feature request conflicts with the Constitution or an accepted ADR:

**STOP. Explain the conflict. Do not implement conflicting code.**

## Current Product Direction

The project is evolving toward:

```text
Probe
  ↓
Doctor
  ↓
Planner
  ↓
Executor
  ↓
Professional GUI
```

Current implementation includes Doctor V3 foundations and Planner Foundation.

The next planned core milestone is Executor Foundation.

The final product is intended to have a professional GUI. CLI work should prioritize
correctness, automation, diagnostics, and CI/CD rather than cosmetic polish.

## Non-Negotiable Architecture

- Doctor is the single source of environment diagnostics.
- Planner consumes Doctor's public `AuditReport`.
- Executor consumes Planner's public `ExecutionPlan`.
- Probe, Doctor, and Planner are read-only.
- Executor is the only write-capable layer.
- CLI and GUI must not bypass the core pipeline.
- CLI and GUI must not duplicate business logic.
- Do not duplicate public models or business rules.
- Consume public models/contracts rather than lower-layer implementation details.

Canonical flow:

```text
Probe → Doctor → Planner → Executor
```

## Implementation Rules

- Never duplicate logic.
- Never bypass accepted ADRs.
- Never redesign architecture without approval.
- Never use quick fixes.
- Never hide architecture problems with broad exception handling.
- Prefer small, explicit, testable changes.
- Preserve backward compatibility.
- Do not introduce runtime dependencies without approval.
- Every feature must include tests.
- Every feature must pass Ruff and Pytest.
- Run relevant CLI smoke tests.
- Keep commits small.
- Never commit directly to `main`.
- One feature = one dedicated branch.
- Stop when architecture is unclear.

## Feature Branch Rule

Start from updated `main`:

```bash
git switch main
git pull
git switch -c feature/<feature-name>
```

After implementation and validation:

```bash
git add <actual-files>
git commit -m "<Conventional Commit>"
git push -u origin feature/<feature-name>
```

Merge only after all required checks pass.

## Validation

Minimum gate:

```bash
git diff --check
ruff check .
pytest
ai-bootstrap audit
ai-bootstrap doctor
ai-bootstrap plan
```

## Current Next Feature

Unless a newer accepted decision changes the roadmap:

```text
feature/executor-foundation
```

Scope:

- Executor public contract;
- execution result model(s);
- consume `ExecutionPlan`;
- explicit safety/write boundary;
- deterministic execution behavior;
- tests.

Do not turn Executor Foundation into a broad autonomous remediation framework.
