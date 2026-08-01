# ADR-001: Application Boundaries and Dependency Direction

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

The command-line presentation, environment audit, and template generation capabilities must evolve without mixing presentation concerns with operating-system and filesystem side effects. Phase 1 requires maintainable simplicity, explicit dependencies, and testable boundaries without introducing unnecessary frameworks.

## Decision

The CLI is the presentation layer and depends on application services. Application services coordinate use cases and depend on typed protocols and domain models. Infrastructure adapters implement those protocols and contain subprocess, platform, packaged-resource, and filesystem side effects. Domain models neither print nor access the filesystem and have no dependency on Typer or Rich.

The application will use small modules and explicit dependency injection. It will not introduce a dependency-injection container, repository pattern, plug-in system, or agent framework.

## Alternatives

- A single-module CLI was rejected because it would mix presentation, coordination, and side effects.
- A framework-based layered architecture was rejected because its added machinery is unnecessary for Phase 1.

## Consequences

The design provides simple test seams and limits coupling at the cost of modest additional module structure. Changes to these boundaries or core interfaces require a new or superseding ADR.
