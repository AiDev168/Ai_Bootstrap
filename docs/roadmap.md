# AI Engineering Bootstrap Roadmap

## Product Direction

The project is evolving from a deterministic bootstrap/audit CLI into a controlled
AI engineering environment platform.

The target product workflow is:

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

The final primary interface is a professional GUI.

CLI remains important for developer workflows, automation, diagnostics, and CI/CD,
but excessive CLI cosmetic work is not a priority.

## Completed Foundation

### Phase 0 — Bootstrap Prototype

**Status: Completed**

Initial project/bootstrap prototype.

### Phase 1 — Core Bootstrap and Validation

**Status: Completed**

Includes:

- environment inspection;
- audit CLI;
- project/template generation;
- typed models;
- deterministic tests;
- safe destination/collision handling.

### Doctor V2

**Status: Completed**

Includes:

- Environment Doctor;
- readiness reporting;
- human-readable diagnostics;
- recommendations.

### Doctor V3 Foundation

**Status: Completed**

Implemented milestones:

1. Model Unification
2. Health Score
3. Check Categorization
4. CI/CD Audit JSON
5. Context-Aware Recommendations

### Planner Foundation

**Status: Completed**

Implemented:

- `ExecutionPlan`;
- `ExecutionPlanAction`;
- stable action IDs;
- deterministic ordering;
- priorities;
- duplicate-action elimination;
- safe handling of unknown checks;
- audit → plan conversion.

## Current Phase — Controlled Execution Pipeline

### Milestone 1 — Executor Foundation

**Status: Next**

Goal: establish the write boundary without building a large remediation framework.

Scope:

- Executor public contract;
- execution result model(s);
- consume `ExecutionPlan`;
- explicit action execution boundary;
- deterministic behavior;
- safety/dry-run semantics where required;
- unit tests;
- integration path for future application/GUI.

Do not add broad autonomous remediation.

### Milestone 2 — Application Workflow

Connect the core services into one workflow:

```text
Doctor
  ↓
Planner
  ↓
Executor
  ↓
Verification / Doctor
```

The resulting application workflow becomes the shared backend for CLI and GUI.

### Milestone 3 — GUI Foundation

Build the professional GUI on top of the application workflow.

Priority:

- environment dashboard;
- Health Score;
- categorized checks;
- recommendations;
- execution plan;
- approval;
- execution progress;
- results/logs;
- re-verification.

Do not duplicate business logic in the GUI.

### Milestone 4 — Safe Remediation Library

Add approved Executor actions incrementally.

Every action requires:

- stable action ID;
- explicit preconditions;
- clear scope;
- deterministic behavior;
- result reporting;
- tests;
- no unrelated side effects.

### Milestone 5 — Bootstrap Workflow

Target experience:

```text
ai-bootstrap bootstrap
```

Conceptually:

```text
Inspect
  ↓
Diagnose
  ↓
Plan
  ↓
Review
  ↓
Approve
  ↓
Execute
  ↓
Verify
```

The GUI should provide the richer interactive version of the same workflow.

## Long-Term Direction

After the deterministic bootstrap/execution core and GUI are stable, the platform
can evolve toward AI-assisted engineering workflows, knowledge integration,
controlled agent capabilities, and other higher-level automation.

Those capabilities are downstream of the stable core and must not destabilize it.
