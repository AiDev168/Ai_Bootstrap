# AI Engineering Bootstrap Constitution

Version: 1.0

Status: Frozen

---

# Primary Goal

Build a production-grade AI Engineering Bootstrap platform.

Correct architecture is always preferred over fast implementation.

No feature is accepted unless it preserves the architecture.

---

# Golden Rules

## Rule 1

Never break an accepted ADR.

If implementation conflicts with an ADR,

stop and ask for approval.

---

## Rule 2

Never redesign an existing subsystem without approval.

Refactor instead of rewrite.

---

## Rule 3

Never duplicate logic.

Every capability must have a single source of truth.

Examples

Doctor

↓

Planner

↓

Executor

Planner must consume Doctor.

Executor must consume Planner.

Never duplicate probing logic.

---

## Rule 4

Respect dependency direction.

Allowed

Probe

↓

AuditService

↓

AuditReport

↓

Planner

↓

ExecutionPlan

↓

Executor

↓

CLI

Forbidden

Planner → Probe

CLI → Probe

Executor → Probe

---

## Rule 5

Never inspect implementation details.

Consume public models only.

Example

GOOD

AuditReport

AuditCheck

ExecutionPlan

BAD

probe.name

probe.status

probe.facts

private attributes

---

## Rule 6

Never use quick fixes.

Forbidden

getattr(...)

monkey patch

temporary hacks

try/except hiding architecture bugs

---

## Rule 7

Every feature must include tests.

No exceptions.

---

## Rule 8

Every feature must pass

ruff check .

pytest

doctor

all existing commands

before it is considered complete.

---

## Rule 9

Never introduce new runtime dependencies without approval.

---

## Rule 10

Backward compatibility is mandatory.

Existing CLI commands must continue working.

---

## Rule 11

All changes must be incremental.

Small commits.

Small pull requests.

No massive rewrites.

---

## Rule 12

Read-only components must remain read-only.

Doctor

Planner

Audit

Probe

must never modify the system.

---

## Rule 13

Executor is the only layer allowed to perform changes.

Everything above it only plans.

---

## Rule 14

Documentation is part of the feature.

Every completed feature updates

README

Architecture

Developer documentation

when required.

---

## Rule 15

Prefer composition over inheritance.

Prefer immutable models.

Prefer explicit code.

Avoid magic.

---

## Rule 16

Never invent architecture.

Follow the repository architecture.

If something is unclear,

ask instead of assuming.

---

## Rule 17

When uncertain,

stop.

Do not guess.

