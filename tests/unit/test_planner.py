#!/usr/bin/env python3
"""Unit tests for the Planner Engine."""

from ai_engineering_bootstrap.audit.models import (
    AuditCheck,
    AuditReport,
    CheckCategory,
    CheckStatus,
    EnvironmentReadiness,
)
from ai_engineering_bootstrap.planner import PlannerEngine


def _make_report(checks: list[AuditCheck]) -> AuditReport:
    """Helper to create a valid AuditReport."""
    readiness = EnvironmentReadiness.calculate(checks)
    return AuditReport(checks=checks, readiness=readiness)


def test_planner_healthy_environment() -> None:
    """Healthy report should yield an empty plan."""
    checks = [
        AuditCheck(name="Git", status=CheckStatus.PASSED, category=CheckCategory.TOOLS),
        AuditCheck(
            name="Python Version",
            status=CheckStatus.PASSED,
            category=CheckCategory.PYTHON,
        ),
    ]
    report = _make_report(checks)
    engine = PlannerEngine()
    plan = engine.generate_plan(report)

    assert plan.is_actionable is False
    assert len(plan.actions) == 0
    assert "No actions" in plan.summary


def test_planner_single_failure() -> None:
    """Single failure should yield one action."""
    checks = [
        AuditCheck(name="Git", status=CheckStatus.FAILED, category=CheckCategory.TOOLS),
        AuditCheck(
            name="Python Version",
            status=CheckStatus.PASSED,
            category=CheckCategory.PYTHON,
        ),
    ]
    report = _make_report(checks)

    engine = PlannerEngine()
    plan = engine.generate_plan(report)
    assert plan.is_actionable is True
    assert len(plan.actions) == 1
    assert plan.actions[0].action_id == "install_git"


def test_planner_multiple_failures_unique() -> None:
    """Multiple failures should yield unique actions."""
    checks = [
        AuditCheck(name="Git", status=CheckStatus.FAILED, category=CheckCategory.TOOLS),
        AuditCheck(
            name="Virtual Environment",
            status=CheckStatus.FAILED,
            category=CheckCategory.ENVIRONMENT,
        ),
        AuditCheck(
            name="Docker", status=CheckStatus.FAILED, category=CheckCategory.CONTAINER
        ),
    ]
    report = _make_report(checks)
    engine = PlannerEngine()
    plan = engine.generate_plan(report)
    assert plan.is_actionable is True
    # ترتیب باید بر اساس پرایوریتی باشد
    assert len(plan.actions) == 3
    assert (
        plan.actions[0].priority < plan.actions[1].priority < plan.actions[2].priority
    )


def test_planner_unknown_failure_graceful() -> None:
    """Unknown failure should not crash and should be ignored or handled gracefully."""
    checks = [
        AuditCheck(
            name="Unknown Weird Check",
            status=CheckStatus.FAILED,
            category=CheckCategory.SYSTEM,
        ),
    ]
    report = _make_report(checks)
    engine = PlannerEngine()
    plan = engine.generate_plan(report)
    # نباید کرش کند. فعلاً نادیده گرفته می‌شود چون مپینگ ندارد.
    assert plan.is_actionable is False
    # یا اگر بخواهیم اکشن عمومی بسازیم، تست را تغییر دهید. فعلاً ایمن‌ترین حالت نادیده گرفتن است.


def test_planner_deterministic_order() -> None:
    """Order of actions must be deterministic."""
    checks = [
        AuditCheck(
            name="Docker", status=CheckStatus.FAILED, category=CheckCategory.CONTAINER
        ),
        AuditCheck(name="Git", status=CheckStatus.FAILED, category=CheckCategory.TOOLS),
    ]
    report = _make_report(checks)
    engine = PlannerEngine()
    plan1 = engine.generate_plan(report)
    # بار دوم با ترتیب معکوس چک‌ها
    checks.reverse()
    report2 = _make_report(checks)
    plan2 = engine.generate_plan(report2)
    assert [a.action_id for a in plan1.actions] == [a.action_id for a in plan2.actions]
