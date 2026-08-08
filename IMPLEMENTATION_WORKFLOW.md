# Implementation Workflow

This workflow is mandatory for every code feature.

## 1. Startup

Before changing code, read in this order:

1. `AGENTS.md`
2. `docs/CONSTITUTION.md`
3. relevant ADRs
4. `docs/PROJECT_CONTEXT.md`
5. `docs/architecture.md`
6. relevant development documentation
7. source code and tests related to the feature

Do not start coding before understanding the current contracts.

## 2. Establish Current State

First inspect:

```bash
git status
git log --oneline --decorate -5
```

Then inspect the relevant source and tests.

Git history and the current source are authoritative for what is already implemented.

Do not reimplement an old feature because a stale document says it is planned.

## 3. Branch

Start every feature from updated `main`.

```bash
git switch main
git pull
git switch -c feature/<feature-name>
```

Never commit directly to `main`.

## 4. Design Review

Identify:

- exact feature scope;
- affected layer;
- public models involved;
- dependencies;
- required tests;
- forbidden changes;
- compatibility impact.

Do not redesign unrelated architecture.

## 5. Architecture Validation

Preserve:

```text
Probe → Doctor → Planner → Executor
```

and the strict boundary:

```text
Probe / Doctor / Planner = read-only
Executor = write
```

CLI and GUI must not become independent business-logic layers.

If architecture is unclear, stop and ask rather than inventing a solution.

## 6. Implementation

Implement the smallest coherent change.

Do not:

- duplicate business logic;
- duplicate public models;
- bypass a layer;
- inspect lower-layer implementation details when a public model exists;
- add speculative abstractions;
- add runtime dependencies without approval;
- change unrelated files;
- hide architecture problems with broad exception handling;
- redesign the project while implementing a feature.

## 7. Tests

Every feature must add or update tests appropriate to the changed behavior.

At minimum:

```bash
pytest
ruff check .
git diff --check
```

Run feature-specific tests as well.

## 8. CLI Smoke Tests

For core workflow changes, run:

```bash
ai-bootstrap audit
ai-bootstrap audit --format json
ai-bootstrap doctor
ai-bootstrap plan
```

Run additional commands relevant to the feature.

## 9. Documentation

Update existing documentation when the accepted architecture, workflow, or product
scope changes.

Do not create documentation merely for trivial implementation details.

The frozen Constitution is not edited casually. Architectural changes are recorded
through ADRs.

## 10. Commit

Stage only the intended feature files.

Use a Conventional Commit.

Example:

```bash
git add <actual-files>
git commit -m "feat(executor): add executor foundation"
```

## 11. Push

```bash
git push -u origin feature/<feature-name>
```

## 12. Merge

Merge only after:

- tests pass;
- Ruff passes;
- `git diff --check` passes;
- smoke tests pass;
- working tree is clean.

After merge:

```bash
git switch main
git pull
git status
git log --oneline --decorate -5
```

## 13. Stop Condition

Once the requested feature is complete and validated, stop.

Do not add unrelated improvements.

The next feature starts as a new branch from the updated `main`.
