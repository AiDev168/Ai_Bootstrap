# Step 32 Product Fix Plan

Product invariants for the intelligent installer:

1. Natural language is authoritative for user intent when an LLM provider is configured.
2. Positive and negative requests must be represented separately; negative requests override positive mentions.
3. English and Persian install requests must be supported.
4. Multiple requested install targets must survive parsing and reconciliation without truncation.
5. Every execution action instance must retain its own action ID and execution context.
6. Approving, rejecting, skipping, or executing one action instance must never alter another action instance.
7. LLM-unavailable mode must be visible as deterministic fallback, not presented as semantic LLM operation.
8. CI gates are strict: ruff check, ruff format check, compileall, pytest.
