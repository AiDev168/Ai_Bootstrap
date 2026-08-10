# AI Engineering Bootstrap Roadmap

## Product Direction

The project is evolving from a deterministic bootstrap/audit CLI into a
controlled AI engineering environment platform.

The target product workflow is:

```text
Inspect
  ↓
Doctor
  ↓
Plan
  ↓
Validate / Safety Policy
  ↓
Human Approval (when required)
  ↓
Execute
  ↓
Verify
  ↓
Recover / Re-plan
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

### Doctor V3 Foundation

**Status: Completed**

Includes:

1. Model Unification
2. Health Score
3. Check Categorization
4. CI/CD Audit JSON
5. Context-Aware Recommendations

### Planner Foundation

**Status: Completed**

Includes:

- `ExecutionPlan`;
- `ExecutionPlanAction`;
- stable action IDs;
- deterministic ordering;
- priorities;
- duplicate-action elimination;
- safe handling of unknown checks;
- audit → plan conversion.

### Controlled Execution Core

**Status: Completed**

Includes:

- Executor Foundation;
- Safe/Mock execution;
- execution-plan validation;
- Action Policy / Safety Gate;
- Safe vs Real execution modes;
- Real Action Handler architecture;
- controlled read-only real action;
- post-execution verification;
- bounded failure/retry/re-plan signalling;
- capability/tool registry.

### Agent / LLM Decision Layer

**Status: Foundation Completed**

Includes:

- structured `AgentDecision`;
- `LLMProvider` contract;
- Mock provider;
- local HTTP provider for LM Studio/Ollama style servers;
- remote API-key provider;
- in-process Python provider;
- capability validation;
- no direct Agent → Executor path.

### Human Approval / Safety Controls

**Status: Foundation Completed**

Includes:

- approval request/result contracts;
- explicit approval provider boundary;
- action/plan/run binding;
- pending/rejected/approved handling;
- fail-closed behavior.

### End-to-End Hardening

**Status: Test Foundation Completed**

The current repository contains hardening tests covering the critical
Doctor → Planner → validation → approval → execution boundaries.

The implementation must continue to preserve these invariants.

## Current Remaining Direction

The controlled core is substantially implemented. Before GUI work, remaining
work must be limited to concrete gaps demonstrated by the current source/tests.

Potential downstream areas, to be taken only when justified by the repository:

1. strengthen end-to-end integration where a current test exposes a real gap;
2. add approved real actions incrementally, each with explicit policy and
   independent verification;
3. complete any required production hardening identified by tests;
4. build the professional GUI only after the controlled backend contracts are
   stable.

Do not introduce a new framework, orchestration model, or autonomous behavior
merely because it is available.

## GUI Foundation

**Status: Deferred**

The GUI is the future primary product interface.

It must consume the existing application/core services and must not duplicate:

- Doctor logic;
- Planner logic;
- Safety Policy;
- Approval logic;
- Executor logic;
- Verification logic.

GUI work begins only after the controlled core is considered stable.

## Long-Term Direction

After the deterministic bootstrap/execution core and GUI are stable, the platform
can evolve toward richer AI-assisted engineering workflows, knowledge integration,
and controlled agent capabilities.

Those capabilities are downstream of the stable core and must not destabilize it.
