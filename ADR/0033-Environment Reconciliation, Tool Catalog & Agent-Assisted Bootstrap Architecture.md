# ADR 0032: Environment Reconciliation, Tool Catalog & Agent-Assisted Bootstrap Architecture

## Status

**Accepted**

## Context

The project must evolve from a controlled Action Executor into an **AI-assisted Environment Orchestrator**.

The existing architecture already provides the core execution and governance pipeline:

```text
Audit
  ↓
Agent / Decision Layer
  ↓
Planner
  ↓
ExecutionPlan
  ↓
Validator
  ↓
Safety Gate / Policy
  ↓
Human Approval
  ↓
Executor
  ↓
Typed Real Handler
  ↓
Verification
  ↓
Recovery / Re-plan
  ↓
Execution Evidence / Audit
```

The current implementation has proven that the execution foundation is functional, including controlled REAL execution, dependency installation, human approval, recovery/re-plan, evidence, and Agent Runtime.

However, the current design is still primarily **Action-centric** rather than **Environment-centric**.

The system can already execute actions such as installing Python packages and can represent tools such as Cursor, Docker, Ruff and other engineering tooling, but it does not yet provide a complete model for:

* defining the user's desired engineering environment;
* comparing the desired environment with the actual environment;
* maintaining a catalog of tools and their supported installation strategies;
* discovering trusted installation artifacts dynamically;
* separating installation, configuration and verification;
* maintaining a persistent workflow/session across multiple Actions;
* exposing approval and progress state through a GUI;
* using the LLM at meaningful decision points such as intent parsing, strategy selection and failure diagnosis;
* proving which evidence and Agent decision led to a particular remediation action.

A practical example exposed this architectural gap.

For Cursor, the official vendor API returned multiple artifacts:

```text
downloadUrl → AppImage
debUrl      → Debian package
rpmUrl      → RPM package
```

The correct installation strategy depended on:

```text
Platform
Architecture
Package format
Privilege level
Trusted source
```

A fixed `install_cursor` implementation alone is therefore insufficient as the long-term abstraction.

The project must support a generic model in which the same orchestration mechanism can eventually handle:

```text
Cursor
Docker
Git
Ruff
Black
Pytest
GitHub CLI
VS Code
Node.js
npm
uv
Poetry
Python
other engineering tools
```

without putting installation-specific logic into the GUI or allowing the LLM to execute arbitrary shell commands.

The existing project baseline must remain backward compatible. Existing `Audit`, `Planner`, `PipelineEngine`, `SafetyGate`, `Approval`, `Executor`, `Verifier`, `Recovery`, `Evidence`, and `Agent Runtime` contracts remain authoritative.

---

## Decision

### 1. Environment Orchestration becomes a first-class application concept

The system will introduce an Environment Orchestration layer above the existing execution pipeline.

The new conceptual flow is:

```text
User Intent
    ↓
EnvironmentRequest
    ↓
Intent Interpretation
    ↓
DesiredEnvironmentState
    +
ActualEnvironmentState
    ↓
Deterministic Reconciliation / Delta
    ↓
Agent Strategy Selection
    ↓
ExecutionPlan
    ↓
Existing Validator / Safety / Approval / Executor
    ↓
Verification
    ↓
Recovery / Re-plan
    ↓
Evidence
```

The existing `PipelineEngine` remains the execution authority.

The new layer does not replace the existing executor architecture.

---

### 2. EnvironmentRequest

A strongly typed `EnvironmentRequest` model will represent what the user wants.

It must support both natural-language and structured input.

Conceptually:

```python
EnvironmentRequest(
    request_id=...,
    project_path=...,
    natural_language_goal=...,
    required_tools=[...],
    optional_tools=[...],
    package_requirements=[...],
    configurations=[...],
    constraints={...},
)
```

Required fields:

```text
request_id
project_path
natural_language_goal
required_tools
optional_tools
package_requirements
configurations
constraints
created_at
```

The natural-language field is optional from the user's perspective but useful for Agent-based intent interpretation.

Structured fields remain authoritative after validation.

LLM output must never be treated as an unvalidated execution instruction.

---

### 3. DesiredEnvironmentState

`DesiredEnvironmentState` becomes a dedicated typed model.

It must not be represented as an arbitrary `dict[str, Any]`.

Conceptually:

```text
DesiredEnvironmentState
├── tools
├── python_packages
├── configurations
├── project_requirements
└── constraints
```

It represents the target state requested by the user.

Examples:

```text
Cursor       REQUIRED
Docker       REQUIRED
Ruff         REQUIRED
Pytest       REQUIRED
Black        OPTIONAL
```

The Desired State is independent from the current machine state.

---

### 4. ActualEnvironmentState

The system will maintain a typed representation of the currently observed environment.

```text
ActualEnvironmentState
├── tools
├── packages
├── configurations
├── system_info
└── probes
```

Existing Audit and Probe infrastructure remains the source of truth for actual observations.

The LLM must never be used to determine whether an objective probe says a tool is installed.

---

### 5. Deterministic Environment Reconciliation

The Reconciliation Service compares:

```text
ActualEnvironmentState
        VS
DesiredEnvironmentState
```

and produces:

```text
EnvironmentDelta
```

Examples:

```text
Cursor:
    desired = required
    actual  = missing
    delta   = install

Docker:
    desired = required
    actual  = installed
    delta   = none

Ruff:
    desired = required
    actual  = missing
    delta   = install
```

The Diff calculation is deterministic.

The LLM is not responsible for deciding whether a probe says "installed" or "missing".

---

### 6. Tool Catalog

A dedicated `ToolCatalog` describes **what a tool is**.

The Tool Catalog is separate from the Action Registry.

```text
Tool Catalog
    ↓
ToolDefinition

Action Registry
    ↓
Action Definition
```

A `ToolDefinition` must include at minimum:

```text
tool_id
display_name
description
supported_platforms
supported_architectures
privilege_level
risk_level
official_sources
supported_artifact_formats
dependencies
```

The catalog must also expose supported lifecycle operations:

```text
detect
discover
install
configure
verify
upgrade
uninstall
```

Not every tool must support every operation.

Capabilities must explicitly declare what is supported.

---

### 7. Action Registry remains operation-centric

The Action Registry describes **what can be done**.

Examples:

```text
install_cursor
configure_cursor
verify_cursor

install_docker
configure_docker
verify_docker

install_python_package
verify_python_package
```

The Tool Catalog and Action Registry must not be merged into one abstraction.

A Tool can have multiple Actions.

An Action can have different Strategies.

---

### 8. Installation Strategy

Installation methods become explicit strategy objects.

Examples:

```text
DebInstallStrategy
AptInstallStrategy
PipInstallStrategy
BinaryInstallStrategy
AppImageInstallStrategy
TarballInstallStrategy
RepositoryInstallStrategy
```

A strategy should expose a controlled lifecycle such as:

```text
discover_artifact
validate_artifact
install
verify
```

Strategies must not provide arbitrary shell execution to the LLM.

---

### 9. ArtifactSource / Provenance

Every discovered installable artifact must carry provenance information.

Required fields:

```text
source_url
source_domain
platform
architecture
format
version
checksum
checksum_algorithm
trust_level
```

Where supported by the upstream source, checksum verification is required or strongly preferred.

`trust_level` must be explicit:

```text
official
verified
community
unknown
```

Artifact URLs must be validated before downloading.

Allowed domains and sources must be defined by Tool Catalog / Policy rather than by Agent-generated strings.

---

### 10. Cursor-specific source behavior

Cursor is the reference implementation for dynamic artifact discovery.

For Linux x86_64, the system must be capable of discovering official vendor metadata and selecting the appropriate DEB artifact when the target system is Debian/Ubuntu.

The Agent may recommend:

```text
DEB > AppImage
```

based on the current platform and desired installation model, but the actual source and package type must be validated deterministically before execution.

The installation Action must not assume that `downloadUrl` is necessarily the correct artifact.

---

### 11. Installation, Configuration and Verification are separate phases

The project will explicitly distinguish:

```text
Install
Configure
Verify
```

Examples:

```text
install_cursor
configure_cursor
verify_cursor
```

Successful installation does not imply successful configuration.

Successful configuration does not imply successful verification.

---

### 12. EnvironmentSession

All environment-oriented operations belong to a central `EnvironmentSession`.

The session tracks:

```text
session_id
request
actual_state
desired_state
delta
plan
status
current_action
approval_states
execution_history
events
agent_decisions
created_at
updated_at
completed_at
```

Session status:

```text
CREATED
AUDITING
PLANNING
AWAITING_APPROVAL
EXECUTING
VERIFYING
RECOVERING
REPLANNING
COMPLETED
FAILED
CANCELLED
```

The GUI renders the Session state rather than reconstructing workflow state from disconnected API calls.

---

### 13. Session persistence boundary

The system will introduce a `SessionStore` abstraction:

```text
create
get
update
append_event
list
```

The first implementation may be in-memory or local persistence, but the interface must be separate from the session model.

The GUI and Backend must depend on the SessionStore abstraction, not its storage implementation.

---

### 14. Approval State

Approval state must use an explicit enum rather than arbitrary strings.

Minimum values:

```text
PENDING
APPROVED
REJECTED
SKIPPED
EXPIRED
```

Approval is per Action.

A user's rejection of one Action must not reject unrelated Actions.

---

### 15. Plan Integrity

The hardening rules from Step 30 remain authoritative.

Environment sessions must preserve:

```text
plan_id
plan_hash
approved_plan_hash
```

If a plan changes after approval:

```text
PLAN_INTEGRITY_VIOLATION
```

must occur and execution must stop.

A new plan requires a new validation/approval cycle.

---

### 16. Agent / LLM roles

LLM participation is divided into three explicit roles.

#### Intent Parser

```text
Natural Language
        ↓
EnvironmentRequest
```

#### Strategy Planner

```text
EnvironmentDelta
+
Tool Catalog
+
Artifact Candidates
        ↓
AgentDecision
```

#### Failure Diagnoser

```text
Failure Evidence
+
Actual State
+
Tool Catalog
        ↓
Recovery Decision
```

The Agent must never bypass:

```text
Validator
Safety Gate
Human Approval
Executor
Verifier
```

---

### 17. AgentDecisionRecord

Every Agent decision must be auditable.

Minimum metadata:

```text
decision_id
session_id
request_id
provider
model
decision_type
reasoning_summary
confidence
selected_capabilities
selected_strategy
input_evidence_ids
created_at
```

The system must not expose raw chain-of-thought.

It must expose a concise `reasoning_summary` suitable for auditing.

Example:

```text
Provider: LM Studio
Model: qwen...
Decision type: strategy_selection
Reason: official DEB is available for Ubuntu x86_64
Confidence: 0.94
Selected capability: install_cursor
Evidence: audit-18, artifact-21
```

---

### 18. LLM fallback behavior

LLM availability must not determine whether basic deterministic safety mechanisms operate.

If LLM is unavailable:

```text
Audit
→ deterministic diff
→ deterministic known strategies
→ normal Planner / Executor
```

must remain possible wherever a known deterministic strategy exists.

The system must never silently fabricate an Agent decision when the LLM is unavailable.

---

### 19. Tool discovery and Strategy selection

The Agent may choose between registered strategies, for example:

```text
Cursor
→ official_deb

Ruff
→ pip_install

Docker
→ approved_os_package

Node
→ approved_vendor_or_repository_strategy
```

The Agent cannot invent a new unrestricted strategy during runtime.

New installation strategies must be implemented and registered in code.

---

### 20. Recovery / Re-plan

A failure with:

```text
replan_recommended = True
```

must be propagated into Recovery.

Recovery flow:

```text
Failure
 ↓
Failure Classification
 ↓
Agent Diagnoser
 ↓
Recovery Plan
 ↓
Validator
 ↓
Safety Gate
 ↓
Human Approval
 ↓
Executor
 ↓
Verification
```

Recovery remains bounded by existing retry/re-plan limits.

---

### 21. Backend API

The Backend becomes a versioned application boundary.

Minimum endpoints:

```text
GET  /api/v1/health
GET  /api/v1/audit
GET  /api/v1/environment
GET  /api/v1/tools

POST /api/v1/environment/request

POST /api/v1/sessions
GET  /api/v1/sessions
GET  /api/v1/sessions/{session_id}

GET  /api/v1/sessions/{session_id}/state
GET  /api/v1/sessions/{session_id}/diff
GET  /api/v1/sessions/{session_id}/plan
GET  /api/v1/sessions/{session_id}/events
GET  /api/v1/sessions/{session_id}/evidence
GET  /api/v1/sessions/{session_id}/agent-decisions

POST /api/v1/sessions/{session_id}/start
POST /api/v1/sessions/{session_id}/actions/{action_id}/approve
POST /api/v1/sessions/{session_id}/actions/{action_id}/reject
POST /api/v1/sessions/{session_id}/actions/{action_id}/skip

POST /api/v1/sessions/{session_id}/recovery
POST /api/v1/sessions/{session_id}/cancel
POST /api/v1/sessions/{session_id}/resume
```

REAL execution must not become an unauthenticated shortcut through HTTP.

---

### 22. Backend Response Envelope

API responses must use a stable envelope:

```json
{
  "api_version": "v1",
  "request_id": "...",
  "status": "ok",
  "data": {}
}
```

Errors:

```json
{
  "api_version": "v1",
  "request_id": "...",
  "status": "error",
  "error": {
    "code": "...",
    "message": "...",
    "details": {}
  }
}
```

---

### 23. GUI

The GUI is an operational client of the Backend.

The GUI must not contain remediation/business logic.

Required views:

#### User Request

```text
Natural-language goal
Structured tool selection
Project path
Constraints
```

#### Current State

```text
Tool
Version
Status
Location
Health
```

#### Desired State

```text
Required
Optional
Package requirements
Configuration requirements
```

#### Diff

```text
Installed
Missing
Mismatched
Needs upgrade
Needs configuration
```

#### Plan Review

Each Action must show:

```text
tool
operation
strategy
source
version
risk
privilege
reason
dependencies
```

#### Approval

Every Action gets independent:

```text
Approve
Reject
Skip
```

#### Execution Timeline

```text
Audit
Intent parsing
Planning
Validation
Approval
Execution
Verification
Recovery
Re-plan
Completion
```

#### Agent Insight

Display:

```text
Provider
Model
Decision type
Reasoning summary
Confidence
Selected capability
Selected strategy
Evidence IDs
```

#### Recovery

Display:

```text
Failure
Diagnosis
Recovery proposal
Required approval
New plan
```

---

### 24. GUI Safety

The GUI must never:

```text
execute shell commands
invoke pip directly
invoke apt directly
invoke sudo directly
call LLM directly for execution
bypass SafetyGate
bypass Approval
```

All mutations go through Backend → Application Service → Pipeline/Executor.

---

### 25. Template evolution

Existing templates must not be overwritten.

Create:

```text
templates/
├── ai-app-template-v1/
└── ai-app-template-v2/
```

`ai-app-template-v2` should support the new environment model.

Minimum:

```text
.cursor/
  rules/

configs/
  environment/

docs/
  architecture/
  decisions/

src/
tests/

environment.yaml
tool-requirements.yaml
```

Example:

```yaml
environment:
  required_tools:
    - python
    - git
    - cursor
    - pytest
    - ruff

  optional_tools:
    - docker
    - github-cli
```

The template expresses Desired State but does not contain the Bootstrap Engine itself.

---

### 26. Security invariants

The following are non-negotiable:

1. LLM cannot execute arbitrary shell commands.
2. LLM cannot bypass SafetyGate.
3. LLM cannot fabricate approval.
4. GUI cannot directly execute REAL Actions.
5. Every mutation requires a registered Action.
6. Every REAL Action requires an approved Policy.
7. External sources must pass provenance validation.
8. Plan changes invalidate previous approval.
9. Package requirements must be validated.
10. File paths must be validated.
11. Privileged Actions must declare their privilege level.
12. Mutating Actions must produce Evidence.
13. LLM decisions must be auditable.
14. Recovery must remain bounded.
15. Unknown Actions remain default-deny.
16. Unknown Tools remain non-executable until explicitly registered.

---

## Consequences

### Positive

* The project becomes an Environment Orchestrator rather than a simple installer.
* User intent becomes a first-class concept.
* Actual vs Desired State becomes deterministic and testable.
* LLM can assist with difficult engineering decisions without becoming an unrestricted executor.
* Cursor becomes one implementation of a generic Tool/Artifact architecture rather than a special-case feature.
* Docker, Ruff, GitHub CLI and future tools can use the same model.
* GUI becomes a Session client rather than a second implementation of the execution engine.
* Recovery and Re-plan become observable and explainable.
* Tool installation provenance becomes auditable.
* The existing Safety/Approval/Executor architecture remains authoritative.

### Negative / Cost

* Additional domain models and persistence abstractions are required.
* Tool installation becomes more structured and requires more implementation per tool.
* GUI implementation becomes more complex because it must render session state.
* LLM orchestration requires stronger observability and validation.
* Artifact discovery and provenance add complexity.
* Persistent sessions require lifecycle management and cleanup.
* Backward compatibility must be maintained with the existing Action Registry and PipelineEngine.

---

## Compatibility Rules

The following existing architectural contracts remain unchanged:

```text
Audit remains the source of actual environment observations.

Planner remains responsible for ExecutionPlan creation.

Validator remains authoritative for plan validity.

SafetyGate remains authoritative for execution permission.

Human Approval remains authoritative for privileged/approved actions.

Executor remains the only mutation execution layer.

Verifier remains independent from the mutating Handler.

Recovery remains bounded.

Execution Evidence remains immutable/auditable.

Agent remains a decision/planning component, never the executor.
```

The new Environment Orchestration layer feeds these existing contracts rather than replacing them.

---

## Migration Strategy

Implementation proceeds incrementally:

```text
Phase A
EnvironmentRequest
DesiredEnvironmentState
ActualEnvironmentState
EnvironmentDelta

Phase B
ToolCatalog
ToolDefinition
ArtifactSource
InstallationStrategy

Phase C
EnvironmentReconciler
Agent strategy selection

Phase D
EnvironmentSession
SessionStore
Session API

Phase E
GUI request/state/diff/plan/approval

Phase F
Live execution/recovery/evidence visualization

Phase G
Template v2
```

At every phase:

```text
Existing tests
+
New tests
```

must remain green.

No previously accepted feature may be removed merely to simplify the new architecture.

---

## Testing Requirements

The new architecture must include tests for:

### EnvironmentRequest

* natural-language input;
* structured input;
* validation;
* invalid tool identifiers;
* duplicate tools.

### Desired/Actual State

* state snapshots;
* tool status;
* version comparison;
* diff calculation.

### Tool Catalog

* lookup;
* supported platform;
* supported architecture;
* strategy lookup;
* unknown tool;
* unknown strategy.

### ArtifactSource

* official source;
* untrusted source;
* domain validation;
* platform mismatch;
* architecture mismatch;
* checksum validation where available.

### Reconciliation

* no-op when states match;
* install missing tool;
* upgrade outdated tool;
* configuration required;
* dependency ordering.

### Agent

* intent parser;
* strategy selection;
* failure diagnosis;
* confidence;
* evidence;
* unavailable provider;
* deterministic fallback.

### Session

* creation;
* state transitions;
* approval;
* rejection;
* execution;
* verification;
* failure;
* recovery;
* resume;
* cancellation.

### Security

* arbitrary URL rejection;
* path traversal rejection;
* package injection rejection;
* Plan tampering rejection;
* unauthorized Action rejection;
* GUI REAL execution rejection;
* Agent shell bypass rejection.

### GUI/API

* current state;
* desired state;
* diff;
* plan;
* approval;
* event timeline;
* evidence;
* recovery;
* error responses;
* concurrent read access.

---

## Definition of Done

ADR 0032 is considered implemented only when the following end-to-end scenario works without mocks:

```text
User opens GUI
        ↓
Writes:
"Prepare this machine for Python AI development.
Install Cursor, Docker, Ruff and Pytest."
        ↓
EnvironmentRequest created
        ↓
Actual State audited
        ↓
Desired State built
        ↓
Deterministic Diff computed
        ↓
Agent chooses installation strategies
        ↓
ExecutionPlan generated
        ↓
GUI shows complete plan
        ↓
User approves Cursor
        ↓
Cursor official artifact discovered
        ↓
Source validated
        ↓
Cursor installed
        ↓
Cursor verified
        ↓
User rejects Docker
        ↓
Docker remains unchanged
        ↓
Ruff installed
        ↓
Verification
        ↓
One Action fails
        ↓
Agent diagnoses failure
        ↓
Recovery plan proposed
        ↓
User approves recovery
        ↓
Re-plan validated
        ↓
Recovery executed
        ↓
Final Desired State calculated
        ↓
Session completed
        ↓
Complete Evidence available
```

The user must be able to see exactly:

```text
What is missing?
Why is it missing?
What will be changed?
Why is this Action proposed?
Which source will be used?
What privileges are required?
What did the Agent decide?
Which model/provider made the decision?
What did the user approve?
What actually happened?
Was it verified?
If it failed, why?
What recovery was proposed?
What is the final environment state?
```

---

## Final Architectural Principle

The project is not a GUI installer.

It is an:

**AI-Assisted Engineering Environment Orchestrator**

with the following separation:

```text
User
  ↓
Intent
  ↓
Desired State
  ↓
Reconciliation
  ↓
Agent Reasoning
  ↓
Planning
  ↓
Governance
  ↓
Controlled Execution
  ↓
Verification
  ↓
Recovery
  ↓
Evidence
```

The GUI is the operational interface to this system.

The LLM is the reasoning layer.

The Planner is the plan generator.

The Safety Gate is the governance boundary.

The Executor is the only mutation authority.

The Verifier is the independent proof boundary.

The Evidence system is the audit boundary.

No layer may silently bypass another layer.

