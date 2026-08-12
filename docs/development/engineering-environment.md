# Engineering Environment Bootstrap

Milestone 29 makes the engineering environment a real, controlled remediation target while preserving the Executor safety boundary.

## Required tooling

- Git
- Pytest
- Ruff
- Cursor desktop

## Optional tooling

- Docker is supported as an engineering/production tool and can be installed when the audit requires it.

## Cursor integration

The repository provides `.cursor/rules/project.mdc` as the canonical Cursor rule set. Generated AI application projects continue to receive their own project rules from `templates/ai-app-template-v1/.cursor/rules/`.

Cursor installation is an explicit typed Executor action. The Linux implementation downloads the official Cursor DEB endpoint and installs it through `apt-get`; it is never executed as a generic shell command.

## Development tooling remediation

Missing Git, Docker, and Cursor findings are converted by Doctor/Planner into explicit actions. REAL execution requires individual human approval for each action. SAFE execution only simulates them.

Pytest and Ruff remain Python dependencies and continue to use the existing dependency-installation workflow.

## Verification

System-tool remediation has independent read-only verifiers:

- Git: executable and version;
- Docker: executable plus active daemon;
- Cursor: executable and version.

The final Doctor audit remains the authoritative readiness check.
