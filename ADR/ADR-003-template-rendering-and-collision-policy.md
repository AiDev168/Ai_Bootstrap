# ADR-003: Template Rendering and Destination Collision Policy

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

Project generation writes multiple files from one of three predefined templates and may encounter invalid input, unsafe paths, or an existing destination. Generation must be deterministic and must not overwrite user data or leave a partial project.

## Decision

The supported template identifiers are `ai-app-template-v1`, `ml-template-v1`, and `ai-research-template-v1`. Templates are distributed as application resources through a catalog. Project names and destination paths are validated before writing. Generation is staged within the destination parent and fails if the final target already exists; no overwrite or merge behavior is provided.

Only declared placeholders in declared UTF-8 text files are replaced. Binary files are copied byte-for-byte. The renderer supports only known variables, including `project_name`, and cleans up staging data after failure. An atomic final rename is used where feasible.

## Alternatives

- Jinja-based rendering was rejected because Phase 1 needs only explicit, allowlisted substitution.
- Merging into an existing directory and overwrite modes were rejected because they risk data loss and weaken deterministic behavior.

## Consequences

Generation is safe, reproducible, and intentionally limited. Adding flexible rendering, merge behavior, or overwrite support requires a new ADR.
