# Git Workflow

## Source of Truth

GitHub is the source of truth for the repository.

The current repository state and Git history are authoritative for implementation
status.

## Golden Rule

Never commit directly to `main`.

Every feature, fix, refactor, test change, or documentation change is developed on
a dedicated branch outside `main`.

## Feature Flow

```text
main
 ↓
git switch main
git pull
 ↓
git switch -c feature/<name>
 ↓
read required project documents
 ↓
inspect current source + tests + Git history
 ↓
implement
 ↓
tests
 ↓
lint / diff checks
 ↓
CLI smoke tests
 ↓
commit
 ↓
push
 ↓
merge to main
 ↓
verify main
```

## Required Startup Reading for Coding AI

Before coding, read:

1. `AGENTS.md`
2. `docs/CONSTITUTION.md`
3. `IMPLEMENTATION_WORKFLOW.md`
4. relevant ADRs
5. `docs/PROJECT_CONTEXT.md`
6. `docs/architecture.md`
7. current source and tests relevant to the feature

Do not assume old documentation describes current implementation status.

## Branch Naming

Use one branch per feature:

```text
feature/<feature-name>
fix/<fix-name>
refactor/<refactor-name>
test/<test-name>
docs/<docs-name>
chore/<chore-name>
```

Examples:

```text
feature/executor-foundation
feature/doctor-v3-health-score
feature/doctor-v3-model-unification
```

## Validation Gate

Before commit:

```bash
git diff --check
ruff check .
pytest
ai-bootstrap audit
ai-bootstrap doctor
ai-bootstrap plan
```

Run feature-specific smoke tests as appropriate.

The working tree must be clean before merge.

## Commit

Use Conventional Commits.

Examples:

```text
feat(executor): add executor foundation
feat(doctor): add context-aware recommendations
fix(doctor): correct readiness calculation
refactor(models): unify audit models
test(planner): add deterministic plan tests
docs: update project architecture
```

Keep commits small and feature-focused.

Do not use placeholder commands such as:

```bash
git add ...
```

Use explicit paths or intentionally stage all intended files.

## Push

```bash
git push -u origin feature/<feature-name>
```

## Merge

Merge only after the feature branch passes its validation gate.

Then return to `main`:

```bash
git switch main
git pull
git status
git log --oneline --decorate -5
```

Confirm the merge is present and the working tree is clean.

Feature branches do not need to be deleted immediately.
