# Step 32 Current Validation

This branch validates the canonical application backend, LLM-aware intent parsing, per-action execution identity, approval isolation, and CI quality gates.

The authoritative runtime path is:

Natural-language goal -> intent parsing -> reconciliation -> strategy planning -> execution-plan validation -> per-action approval -> canonical executor -> verification/evidence.

Do not use the legacy in-module session state path. Run the supported GUI through the canonical backend/server entry point or the FastAPI compatibility layer, both of which delegate to `ApplicationBackend`.
