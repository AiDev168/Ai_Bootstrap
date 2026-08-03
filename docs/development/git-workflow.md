# Git Workflow

## Source of Truth

GitHub is the single source of truth.

## Development

Development may be performed on any workstation using a valid Git clone.

## Branch Strategy

Never commit directly to main.

Allowed prefixes:

- feature/
- fix/
- docs/
- refactor/
- test/
- chore/

## Validation

Every branch must pass on Ubuntu:

- pytest
- ruff check .
- ai-bootstrap audit

before merge.

## Merge Policy

Merge only after Ubuntu validation.

## Commit Convention

Use Conventional Commits.

## Versioning

Stable milestones should be tagged.
