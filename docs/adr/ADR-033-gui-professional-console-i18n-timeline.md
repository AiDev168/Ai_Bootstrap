# ADR-033: Professional GUI Console, Localization, and Timeline Semantics

## Status
Accepted.

## Context
The GUI must be an operational interface, not a transient status page. Request history must remain inspectable while polling continues. Per-action controls must remain isolated. LLM health must be reported from the backend rather than inferred from page load. The interface must support English/Persian without translating identifiers such as package names, tool IDs, commands, URLs, model IDs, or API routes.

## Decisions

1. Request Console keeps a bounded history of the most recent 100 requests. Polling and normal refresh operations never clear that history. The existing Clear action remains an explicit user action.
2. The Latest Response panel has Pause/Resume. Pause freezes automatic replacement of the selected response while new request records continue to accumulate.
3. Clicking any Request Console entry selects that exact request and displays its response or error in Latest Response.
4. Request records are filterable by All, GET, POST, or Errors. HTTP failures and network failures have a red visual state.
5. Dashboard LLM status is based on a live backend probe. A cached or merely configured provider must not be shown as connected.
6. The GUI has an explicit EN/FA language switch. User-facing UI strings are translated; package names, tool IDs, action IDs, commands, URLs, model IDs, and protocol paths are preserved verbatim.
7. Session Timeline events are classified by lifecycle stage: session, intent, plan, approval, execution, verification, recovery, and error. Each stage has a distinct visual marker and a legend.
8. Safe mode is explicitly communicated as a dry-run/preview and Real mode as canonical installation/execution.
9. GUI contract tests validate semantic behavior rather than depending on incidental implementation names.

## Consequences
The GUI becomes a persistent operational debugging surface. Request history, exact responses/errors, language state, and lifecycle stages remain visible while polling continues. This adds client-side state but materially improves diagnosability and user trust.
