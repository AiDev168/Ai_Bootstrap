# Step 32 Hardening Plan

This branch consolidates the runtime session path around the application backend and makes natural-language intent authoritative before reconciliation.

## Invariants

1. The HTTP session API must delegate to `ApplicationBackend` / `RuntimeSessionService`; it must not maintain a parallel `SessionStore` execution path.
2. Every requested item must have an explicit action (`install`, `skip`, `remove`, `upgrade`, or `unknown`). Explicit negative intent is a hard constraint.
3. Multiple requested items must remain independently addressable from intent through execution and verification.
4. REAL approval applies to action instances, never to a shared canonical handler ID.
5. LLM provider output is structured, validated against the tool catalog, and recorded as an agent decision. Deterministic parsing is fallback only.
6. Safe/CI tests must not bypass the same production boundaries they claim to validate.
