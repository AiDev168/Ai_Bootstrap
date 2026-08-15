# ADR-033: Professional GUI Console, Localization, and Timeline Semantics

## Status
Accepted for feature/gui-professional-console-i18n-timeline.

## Context
The GUI is operationally useful only when request history, execution actions, and lifecycle events remain inspectable. Polling must not erase debugging evidence. Per-action controls must remain isolated. The dashboard must accurately report LLM connectivity. The interface also needs English/Persian localization without translating package, tool, command, or protocol identifiers.

## Decisions

1. Request Console keeps a bounded in-memory history of the most recent 100 requests. No refresh operation clears history. Filtering is a view operation only.
2. The Latest Response panel supports Pause/Resume. Pausing stops automatic replacement of the selected response while request history continues to accumulate.
3. Clicking any request-console entry selects that entry and renders its exact response/error in Latest Response.
4. Request entries are classified as GET/POST/OTHER. HTTP failures and network failures use a red visual state.
5. Dashboard/server health is authoritative per successful health probe. LLM availability is shown from the backend health payload and is not inferred from page load.
6. GUI localization uses an explicit language selector. User-facing labels are translated; package names, tool IDs, action IDs, commands, URLs, model IDs, and protocol paths remain unchanged.
7. Timeline events have semantic categories (session, intent, plan, approval, execution, verification, recovery, error). Each category has a distinct visual marker/color and a legend.
8. Safe execution remains a dry-run/preview path. Real execution is the canonical installation path. GUI labels must communicate this distinction clearly.
9. All GUI behavior above is covered by contract tests that assert semantics, not incidental implementation names.

## Consequences
The GUI becomes a debugging console rather than a transient status dashboard. Request history remains inspectable, localization is deterministic, and lifecycle events can be correlated to pipeline stages. This intentionally increases frontend state handling but reduces operational ambiguity.
