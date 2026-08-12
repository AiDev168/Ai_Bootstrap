# ADR 0032: Environment Reconciliation, Tool Catalog & Agent-Assisted Bootstrap Architecture

## Status
Accepted (with revisions)

## Context
The project has evolved from a simple "Action Executor" to a full "Environment Orchestrator".
Previous attempts to install tools like Cursor revealed gaps in:
1. Distinguishing between "Tool Metadata" and "Action Definitions".
2. Handling "Desired State" vs. "Actual State" reconciliation.
3. Managing artifact provenance and source trust.
4. Providing a session-centric view for the GUI.
5. Integrating LLM assistance without compromising safety or determinism.

We need a formal architecture to support Steps 28–33, enabling users to define high-level goals (e.g., "Prepare Python AI Env") and having the system safely plan, approve, execute, and verify the necessary changes.

## Decision
We adopt a **Reconciliation Loop Architecture** driven by a **Session-Centric Backend** and assisted by **Agent/LLM** for intent parsing and strategy selection, while keeping core logic deterministic.

### 1. Data Contracts (Models)

#### A. Desired State (`DesiredEnvironmentState`)
No longer a free-form `dict`. It is a structured model:
- `tools`: Map of `tool_id` -> `ToolRequirement` (REQUIRED/OPTIONAL/ABSENT)
- `python_packages`: List of package specs
- `configurations`: Key-value pairs for tool configs
- `project_requirements`: Path to requirements file or inline list
- `constraints`: Platform/version constraints

#### B. Tool Definition & Lifecycle (`ToolDefinition`)
Each tool in the catalog defines a full lifecycle, not just installation:
- `detect`: How to check presence/version
- `discover`: How to find artifacts/sources
- `install`: Installation strategy
- `configure`: Configuration steps
- `verify`: Verification command/check
- `upgrade`: Upgrade strategy
- `uninstall`: Removal strategy

#### C. Artifact Provenance (`ArtifactSource`)
Strict metadata for every downloadable artifact:
- `url`: Direct download URL
- `platform` / `architecture`: Target compatibility
- `format`: e.g., deb, rpm, tar.gz, wheel
- `version`: Specific version
- `checksum` / `checksum_algorithm`: For integrity (mandatory for remote trusted sources)
- `trust_level`: OFFICIAL, COMMUNITY, USER_PROVIDED
- `source_domain`: Allowed domain validation

#### D. Session State (`EnvironmentSession`)
The central unit of work for the GUI:
- `session_id`, `created_at`, `updated_at`
- `request`: The original `EnvironmentRequest`
- `actual_state`: Snapshot at start
- `desired_state`: Target state
- `delta`: Computed differences
- `plan`: The `ExecutionPlan` generated
- `approval_states`: Map of `action_id` -> `ApprovalStatus` (PENDING/APPROVED/REJECTED/SKIPPED/EXPIRED)
- `execution_history`: List of `SessionActionResult` (structured, not `Any`)
- `evidence`: List of immutable `SessionEvidence` records
- `plan_integrity`: `plan_hash` and `approved_plan_hash` to detect tampering

#### E. Agent Decision Record (`AgentDecisionRecord`)
Transparent logging of LLM involvement:
- `provider`, `model`
- `decision_type`: INTENT_PARSING, STRATEGY_SELECTION, DIAGNOSIS
- `reasoning_summary`: Human-readable explanation (no raw CoT)
- `confidence`: 0.0–1.0 score
- `input_evidence_ids`: List of evidence IDs used for this decision
- `selected_capabilities`: List of chosen actions/tools

### 2. Architectural Flow

```text
User Intent
    ↓
EnvironmentRequest
    ↓
[Optional] LLM Intent Parser → DesiredEnvironmentState
    ↓
ActualEnvironmentState (via Probes)
    ↓
Deterministic Reconciler → Delta (Missing/Extra/Mismatched)
    ↓
Tool Catalog (Strategies)
    ↓
[Optional] LLM Strategy Planner → Recommended Actions
    ↓
Planner → ExecutionPlan
    ↓
Validator + Safety Gate
    ↓
Per-Action Human Approval
    ↓
Executor → Typed Handlers
    ↓
Verifier
    ↓
Failure? → [Optional] LLM Diagnoser → Recovery Plan → (Loop back to Approval)
    ↓
Success → Update Evidence & Actual State
