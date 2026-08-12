# Engineering Environment Bootstrap

Milestone 29 establishes the engineering-environment contract without bypassing the
Executor safety boundary.

## Required tooling

- Git
- Pytest
- Ruff

## Optional tooling

- Docker
- Cursor CLI

## Cursor integration

The repository provides `.cursor/rules/project.mdc` as the canonical Cursor rule set.
Generated AI application projects continue to receive their own project rules from
the existing template under `templates/ai-app-template-v1/.cursor/rules/`.

## Safety boundary

This milestone does not install operating-system tools or the Cursor binary directly.
Such mutations require explicit typed Executor handlers and policies. The engineering
service is therefore read-only and reports what is present and what is missing.
