"""Tests for the stable backend API and GUI HTTP boundary."""

import json

from ai_engineering_bootstrap.backend.service import ApplicationBackend


def test_backend_exposes_versioned_read_models() -> None:
    backend = ApplicationBackend()

    audit = backend.audit().data
    plan = backend.plan().data
    engineering = backend.engineering().data

    assert "readiness" in audit
    assert "actions" in plan
    assert "tools" in engineering
    assert isinstance(plan["actions"], list)


def test_backend_safe_run_preserves_pipeline_contract() -> None:
    backend = ApplicationBackend()
    result = backend.run_safe().data

    assert "audit" in result
    assert "plan" in result
    assert "validation" in result
    assert "execution" in result
    assert "verification" in result
    assert "evidence" in result


def test_real_api_is_explicitly_blocked_at_backend_boundary() -> None:
    result = ApplicationBackend().run_real_requires_cli().data
    assert result["allowed"] is False
    assert "interactive approval" in result["message"]


def test_gui_handler_health_route_serializes_json() -> None:
    class FakeHandler:
        backend = ApplicationBackend()

    payload = FakeHandler.backend.audit().data
    encoded = json.dumps(payload).encode("utf-8")
    assert encoded.startswith(b"{")
    assert "readiness" in payload


def test_backend_version_is_stable() -> None:
    assert ApplicationBackend.VERSION == "v1"
