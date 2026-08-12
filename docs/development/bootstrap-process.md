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

The engineering environment service is read-only and reports:

- Git;
- Pytest;
- Ruff;
- Docker when available;
- Cursor CLI when available;
- canonical repository Cursor rules.

The repository rules are stored in `.cursor/rules/project.mdc`. Generated AI projects
continue to receive the existing template rules under
`templates/ai-app-template-v1/.cursor/rules/`.

Operating-system tool installation and Cursor binary installation are intentionally
not implemented as generic shortcuts. They require explicit typed Executor handlers,
policies, approvals, and verifiers.
