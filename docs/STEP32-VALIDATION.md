# Step 32 validation

The GUI bootstrap flow must preserve these boundaries:

1. Natural-language intent is parsed by the configured LLM provider when enabled; deterministic parsing is an explicit fallback.
2. Strategy selection uses only strategies registered in the Tool Catalog.
3. Python package actions carry independent action IDs such as `install_python_package:ruff` and `install_python_package:pytest`.
4. Approve, reject, or skip applies only to the selected action instance.
5. Execution uses the canonical executor and verifier pipeline.
6. Real execution never bypasses SafetyGate or human approval.
7. Test Connection does not persist unsaved LLM settings.
8. Network LLM providers use the configured `base_url`, model, and optional API key.
9. Each execution result is recorded in session evidence and exposed to the GUI.

Required CI gates:

```bash
python -m ruff check .
python -m ruff format --check .
python -m compileall -q src tests
pytest -q
```
