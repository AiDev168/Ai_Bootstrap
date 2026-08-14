"""Unit tests for the Recommendation Engine."""

from ai_engineering_bootstrap.audit.models import AuditCheck, CheckCategory, CheckStatus
from ai_engineering_bootstrap.audit.recommendations import RecommendationEngine


def test_recommendation_for_passed_check():
    check = AuditCheck(
        name="Python Version",
        status=CheckStatus.PASSED,
        category=CheckCategory.PYTHON,
        details="3.9.0",
        facts={"current": "3.9.0"},
    )
    assert RecommendationEngine.generate(check) == []


def test_recommendation_for_virtual_environment_failure():
    check = AuditCheck(
        name="Virtual Environment",
        status=CheckStatus.FAILED,
        category=CheckCategory.ENVIRONMENT,
        facts={"in_venv": "False"},
    )
    recs = RecommendationEngine.generate(check)
    assert any("virtual environment" in r.lower() for r in recs)
    assert any("activate" in r.lower() for r in recs)


def test_recommendation_for_editable_install_failure():
    check = AuditCheck(
        name="Editable Install",
        status=CheckStatus.FAILED,
        category=CheckCategory.ENVIRONMENT,
    )
    recs = RecommendationEngine.generate(check)
    assert any("pip install -e" in r for r in recs)


def test_recommendation_for_missing_dependency():
    check = AuditCheck(
        name="Ruff", status=CheckStatus.FAILED, category=CheckCategory.DEPENDENCIES
    )
    recs = RecommendationEngine.generate(check)
    assert any("ruff" in r.lower() for r in recs)
    assert any("pip install" in r.lower() for r in recs)


def test_recommendation_for_git_failure():
    check = AuditCheck(
        name="Git", status=CheckStatus.FAILED, category=CheckCategory.TOOLS
    )
    recs = RecommendationEngine.generate(check)
    assert any("git" in r.lower() for r in recs)


def test_duplicate_removal_in_consolidated_list():
    check1 = AuditCheck(
        name="Typer", status=CheckStatus.FAILED, category=CheckCategory.DEPENDENCIES
    )
    check2 = AuditCheck(
        name="Rich", status=CheckStatus.FAILED, category=CheckCategory.DEPENDENCIES
    )

    # فرض می‌کنیم هر دو یک توصیه مشابه تولید نمی‌کنند اما اگر بکنند باید حذف شود
    # اینجا تست منطق unique بودن در generate_for_all است
    all_recs = RecommendationEngine.generate_for_all([check1, check2])
    assert len(all_recs) == len(set(all_recs))


def test_empty_recommendations_for_healthy_environment():
    checks = [
        AuditCheck(
            name="Python Version",
            status=CheckStatus.PASSED,
            category=CheckCategory.PYTHON,
        ),
        AuditCheck(name="Git", status=CheckStatus.PASSED, category=CheckCategory.TOOLS),
    ]
    recs = RecommendationEngine.generate_for_all(checks)
    assert recs == []
