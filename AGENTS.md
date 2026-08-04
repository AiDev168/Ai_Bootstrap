# AI Engineering Bootstrap

Project Constitution

This document defines the mandatory implementation rules.

These rules override feature prompts.

If a feature conflicts with this document,

STOP and explain the conflict.

Never implement conflicting code.

------------------------------------------------

Priority

1. Constitution

2. Accepted ADRs

3. Architecture

4. Feature Prompt

------------------------------------------------

Implementation Rules

- Never duplicate logic.
- Never bypass ADRs.
- Never redesign architecture.
- Never use quick fixes.
- Never inspect internal implementation.
- Consume public models only.
- Doctor is the single source of diagnostics.
- Planner consumes Doctor.
- Executor consumes Planner.
- Read-only components never modify the system.
- Every feature updates tests.
- Every feature passes Ruff and Pytest.
- Backward compatibility is mandatory.
- Prefer refactoring over rewriting.
- Small commits only.
- Stop when architecture is unclear.
