# Bootstrap Process

## Product Workflow

The bootstrap process is a controlled environment workflow, not merely a checklist.

```text
Inspect
  ↓
Doctor
  ↓
Plan
  ↓
Validate
  ↓
Review / Approve
  ↓
Execute
  ↓
Verify
  ↓
Doctor again
```

## Milestone 28 — End-to-End Environment Bootstrap

`EnvironmentBootstrapService` is the application-level orchestrator. It does not
contain remediation handlers and does not bypass the existing `PipelineEngine`.

In REAL interactive mode, every approval-required action is handled independently:

1. create an approval request for the current typed action;
2. ask the user for that action only;
3. execute it immediately when approved;
4. skip it when rejected;
5. continue to the next planned action;
6. perform a final read-only Doctor audit.

This preserves the required behavior for plans containing multiple instances of the
same action ID, such as separate Python package installations.

## Milestone 29 — Engineering Environment Bootstrap

The engineering environment contract now participates in the same controlled remediation path. Doctor reports Git, Docker, and Cursor state; Planner maps missing tools to typed actions; Executor performs only approved real actions; independent verifiers confirm the result.

The repository rules are stored in `.cursor/rules/project.mdc`. Generated AI projects continue to receive the existing template rules under `templates/ai-app-template-v1/.cursor/rules/`.

REAL execution uses explicit handlers for Git, Docker, and Cursor. Each action requires its own human approval. No generic shell execution capability is introduced.
