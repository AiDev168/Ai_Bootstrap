# Project Context — Master Development Reference

## Project Identity

**Repository:** `aamm188/ai-engineering-bootstrap`

GitHub is the source of truth.

Reference development runtime: Ubuntu 24.04 LTS.

## Product Goal

Build a controlled AI Engineering Bootstrap platform that can:

1. inspect an engineering environment;
2. diagnose its state;
3. calculate readiness and health;
4. generate a deterministic remediation plan;
5. let the user review/approve that plan;
6. execute only explicitly permitted actions;
7. verify execution independently;
8. expose the same core workflow to CLI and the future professional GUI;
9. support controlled AI/LLM decision-making without giving the model direct execution authority.

Target workflow:

```text
Environment
   ↓
Inspect / Probes
   ↓
Doctor / AuditService
   ↓
AuditReport
   ↓
Planner
   ↓
ExecutionPlan
   ↓
Validate / Safety Policy
   ↓
Human Approval (when required)
   ↓
Executor
   ↓
Verification
   ↓
Recovery / Re-plan Signal
   ↓
Final Result
```

## Current Implementation Status

The following foundations are present in the current `main` source tree and Git history:

- Bootstrap foundation
- Environment probes
- AuditService / Doctor
- unified Doctor audit models
- development and production readiness
- Health Score
- check categorization
- deterministic audit JSON / CI output
- context-aware recommendations
- Planner Foundation
- ExecutionPlan / ExecutionPlanAction
- stable action IDs and deterministic ordering
- Executor Foundation
- Safe/Mock handlers
- Safe/Real execution modes
- Action Policy / Safety Gate
- Real Action Handler architecture
- controlled read-only real execution (`check_python_version_real`)
- post-execution verification contracts and Python version verifier
- bounded retry / failure classification / re-plan signalling
- Capability / Tool Registry
- Agent / LLM Decision Layer
- Local-server, API-key, and in-process provider contracts
- Human Approval / Safety Controls
- End-to-End hardening tests

## Current Baseline

`main` is the stable integration branch.

The current repository state, source code, tests, and Git history are authoritative.
Older roadmap statements must not be interpreted as current status.

## Architecture

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
Validation / Safety Policy
  ↓
Human Approval (conditional)
  ↓
Executor
  ↓
Independent Verification
  ↓
Recovery / Re-plan Signal
```

The Agent/LLM layer is a decision producer, not an execution layer:

```text
CapabilityRegistry
       ↓
Agent / LLM Decision Engine
       ↓
structured decision
       ↓
Planner
       ↓
ExecutionPlan
       ↓
controlled execution path
```

Provider implementations are behind the `LLMProvider` contract. The current
provider foundation covers:

- local HTTP servers such as LM Studio / Ollama;
- remote API-key providers;
- in-process Python model providers;
- mock provider for deterministic tests.

## Responsibilities

**Probe**

Read-only environment observation.

**Doctor / AuditService**

Single source of diagnostics. Produces readiness, Health Score, categories,
recommendations, and `AuditReport`.

**Planner**

Consumes `AuditReport` and produces deterministic `ExecutionPlan`.

**Agent / LLM Decision Layer**

Produces structured capability selections for Planner. It must not directly
invoke Executor, handlers, subprocesses, or shell commands.

**Safety / Policy**

Evaluates whether a proposed action is permitted for the current execution mode
and approval state. Unknown or unregistered actions are denied.

**Human Approval**

Provides explicit approval for actions whose policy requires it. Approval is
bound to the relevant action/plan/run context.

**Executor**

Consumes the validated plan and dispatches only registered handlers.

**Verification**

Independently observes execution outcomes and does not trust executor messages
as proof of environmental state.

**Recovery**

Classifies failures and applies bounded retry/re-plan/stop decisions. It must
not bypass Safety Gate.

**CLI**

Developer, diagnostic, automation, and CI/CD interface.

**GUI**

Long-term primary product interface. It must use the same core/application
services and must not duplicate business logic.

## Frozen Rules

- Never duplicate business logic.
- Never duplicate Doctor models.
- Doctor is the source of truth for diagnostics.
- Planner consumes Doctor public models.
- Agent/LLM does not execute actions.
- Executor consumes Planner public models.
- Executor dispatches only registered handlers.
- Safety Gate is fail-closed.
- Human approval cannot be bypassed by the model or CLI.
- Verification is independent and read-only.
- Retry cannot bypass Safety Gate.
- CLI/GUI cannot bypass the controlled pipeline.
- Backward compatibility is mandatory.
- No unnecessary runtime dependencies.
- No speculative abstractions.
- No unrelated refactors during feature implementation.
- Every feature is tested.
- `main` is not modified directly for feature work; feature work uses a branch
  and is merged after verification.
- The GUI is intentionally deferred until the controlled core is stable.

## Development Workflow

Every feature:

```text
updated main
    ↓
feature branch
    ↓
read project rules + inspect current code
    ↓
implement smallest coherent change
    ↓
tests
    ↓
ruff
    ↓
git diff --check
    ↓
CLI smoke tests
    ↓
commit
    ↓
push
    ↓
merge
    ↓
verify main
```

## Mandatory AI Startup

A coding AI must read:

```text
AGENTS.md
docs/CONSTITUTION.md
relevant ADRs
IMPLEMENTATION_WORKFLOW.md
docs/PROJECT_CONTEXT.md
docs/architecture.md
relevant source/tests
```

Then inspect:

```bash
git status
git branch --show-current
git log --oneline --decorate -5
```

The current repository and Git history override stale planning text.

## Product Priority

Priority order:

```text
1. Correct and testable controlled core
2. Doctor → Planner → controlled execution workflow
3. Safety, approval, verification, and deterministic recovery
4. Agent/LLM integration behind explicit contracts
5. End-to-end hardening
6. Professional GUI
7. CLI cosmetic improvements
```

The CLI remains a development, diagnostic, automation, and CI/CD interface.
The professional GUI is deliberately downstream of the stable core.
