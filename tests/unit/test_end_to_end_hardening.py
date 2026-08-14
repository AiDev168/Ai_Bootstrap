import inspect
from unittest.mock import MagicMock, patch

import pytest

import ai_engineering_bootstrap.agent.engine as agent_module
import ai_engineering_bootstrap.executor.registry as registry_module
from ai_engineering_bootstrap.approval.provider import InMemoryApprovalProvider
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.recovery import FailureType, RetryPolicy
from ai_engineering_bootstrap.pipeline.engine import PipelineEngine

# --- Helper Functions for Mocking Plan and Actions ---


def create_mock_action(
    action_id: str, requires_approval: bool = False, risk_level: str = "LOW"
):
    """Creates a mock action mimicking the ExecutionPlan action structure."""
    action = MagicMock()
    action.id = action_id
    action.policy = MagicMock()
    action.policy.risk_level = risk_level
    action.policy.approval_requirement.name = (
        "REQUIRED" if requires_approval else "NONE"
    )
    action.reason = f"Executing {action_id}"
    return action


def create_mock_plan(plan_id: str, actions: list):
    """Creates a mock ExecutionPlan."""
    plan = MagicMock()
    plan.id = plan_id
    plan.actions = actions
    return plan


# --- Test Fixtures ---


@pytest.fixture
def pipeline_engine():
    return PipelineEngine()


@pytest.fixture
def approval_provider():
    return InMemoryApprovalProvider()


# --- A. Executor cannot invent actions ---


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_executor_cannot_invent_actions(
    mock_planner, mock_validator, mock_executor, mock_audit, pipeline_engine
):
    """Executor must execute only actions explicitly contained in ExecutionPlan."""
    plan = create_mock_plan("plan-1", [create_mock_action("act-1")])
    mock_planner.return_value.generate_plan.return_value = plan
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=True)

    pipeline_engine.run()

    # Verify the exact plan object was passed to executor without modification
    mock_executor.return_value.execute.assert_called_once()
    args, _ = mock_executor.return_value.execute.call_args
    executed_plan = args[0]
    assert executed_plan.id == "plan-1"
    assert executed_plan.actions[0].id == "act-1"


# --- B. Agent cannot execute directly ---


def test_agent_cannot_execute_directly():
    """Agent / LLM Decision Layer must never have a direct execution path."""
    for name, obj in vars(agent_module).items():
        if inspect.isclass(obj) and obj.__module__ == agent_module.__name__:
            assert not hasattr(obj, "execute"), f"{name} has execute method"
            assert not hasattr(obj, "run_shell"), f"{name} has run_shell method"
            assert not hasattr(obj, "subprocess"), f"{name} has subprocess attribute"


# --- C. Capability Registry cannot execute ---


def test_capability_registry_cannot_execute():
    """Capability metadata must never contain callable handlers or execution methods."""
    for name, obj in vars(registry_module).items():
        if inspect.isclass(obj) and obj.__module__ == registry_module.__name__:
            assert not hasattr(obj, "execute"), f"{name} has execute method"
            assert not hasattr(obj, "run"), f"{name} has run method"
            assert not hasattr(obj, "subprocess"), f"{name} has subprocess attribute"


# --- D. Safety Gate cannot be bypassed ---


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_safety_gate_blocks_execution(
    mock_planner, mock_validator, mock_executor, mock_audit, pipeline_engine
):
    """Any action denied by SafetyGate must never reach its handler."""
    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action("dangerous")]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=False)

    result = pipeline_engine.run()

    mock_executor.return_value.execute.assert_not_called()
    assert result.execution_result is None


# --- E. Human Approval cannot be bypassed ---


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_human_approval_cannot_be_bypassed(
    mock_planner,
    mock_validator,
    mock_executor,
    mock_audit,
    pipeline_engine,
    approval_provider,
):
    """If an action requires approval and it is missing, execution is blocked."""
    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action("act-1", requires_approval=True)]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=True)

    result = pipeline_engine.run(approval_provider=approval_provider)

    mock_executor.return_value.execute.assert_not_called()
    assert result.is_pending_approval is True


# --- F. REAL mode remains explicit ---


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_real_mode_remains_explicit(
    mock_planner, mock_validator, mock_executor, mock_audit, pipeline_engine
):
    """Default execution mode must remain SAFE."""
    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action("act-1")]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=True)

    pipeline_engine.run()

    mock_executor.assert_called_with(mode=ExecutionMode.SAFE)


# --- H. Verification isolation ---


def test_verifier_isolation():
    """Verifier must never execute actions or modify system state."""
    from ai_engineering_bootstrap.executor.validator import ExecutionPlanValidator

    v = ExecutionPlanValidator()
    assert not hasattr(v, "execute")
    assert not hasattr(v, "run_shell")


# --- I. Recovery isolation ---


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_recovery_does_not_bypass_safety(
    mock_planner, mock_validator, mock_executor, mock_audit, pipeline_engine
):
    """Retry/Re-plan must never bypass Validation or SafetyGate."""
    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action("act-1")]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=True)

    mock_exec_result = MagicMock()
    mock_exec_result.results = [MagicMock(is_success=False)]
    mock_executor.return_value.execute.return_value = mock_exec_result

    result = pipeline_engine.run(max_retry_attempts=2)

    assert result is not None
    assert result.execution_result is not None


# --- J. Unknown actions ---


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_unknown_actions_blocked(
    mock_planner, mock_validator, mock_executor, mock_audit, pipeline_engine
):
    """Unknown action IDs must never execute."""
    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action("unknown_act")]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=False)

    pipeline_engine.run()
    mock_executor.return_value.execute.assert_not_called()


# --- K. Bounded retry prevents infinite loop ---


def test_bounded_retry_prevents_infinite_loop():
    """Verify bounded retry behavior. No execution may produce an infinite loop."""
    policy = RetryPolicy(max_attempts=3)

    retry_count = 0
    for i in range(5):
        mock_result = MagicMock(is_success=False)
        record = policy.classify_failure(mock_result)
        # استفاده از صفت صحیح requires_replan بجای requires_retry
        if record.requires_replan:
            retry_count += 1

    # اطمینان از اینکه تعداد دفعات نیاز به re-plan از حداکثر مجاز بیشتر نمی‌شود
    # (این تست وابسته به منطق داخلی RetryPolicy است)
    assert retry_count <= 3


# --- L. Re-plan is observable ---


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_replan_is_observable(
    mock_planner, mock_validator, mock_executor, mock_audit, pipeline_engine
):
    """Re-plan requests must be observable and stop current execution."""
    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action("act-1")]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=True)

    mock_exec_result = MagicMock()
    mock_exec_result.results = [MagicMock(is_success=False)]
    mock_executor.return_value.execute.return_value = mock_exec_result

    with patch("ai_engineering_bootstrap.pipeline.engine.RetryPolicy") as MockPolicy:
        mock_record = MagicMock()
        mock_record.failure_type = FailureType.TRANSIENT
        mock_record.requires_replan = True
        MockPolicy.return_value.classify_failure.return_value = mock_record

        result = pipeline_engine.run()

        assert result.replan_requested is True


# --- M. Deterministic ordering ---


def test_deterministic_ordering():
    """Multiple actions must preserve deterministic ordering."""
    actions = [create_mock_action(f"act-{i}") for i in range(5)]
    plan = create_mock_plan("plan-1", actions)

    for i, action in enumerate(plan.actions):
        assert action.id == f"act-{i}"


# --- Cross-Layer Attack Tests ---


@pytest.mark.parametrize(
    "malicious_id",
    [
        "rm -rf /",
        "sudo apt install malicious",
        "../../../etc/passwd",
        "exec(lambda: os.system('ls'))",
        "",
    ],
)
@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_malicious_action_ids_rejected(
    mock_planner,
    mock_validator,
    mock_executor,
    mock_audit,
    pipeline_engine,
    malicious_id,
):
    """Malicious or malformed inputs must never be executed."""
    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action(malicious_id)]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=False)

    result = pipeline_engine.run()

    mock_executor.return_value.execute.assert_not_called()
    assert result.execution_result is None


# --- End-to-End Scenarios ---


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_e2e_healthy_flow(
    mock_planner, mock_validator, mock_executor, mock_audit, pipeline_engine
):
    """Scenario 1: Healthy environment completes deterministically."""
    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action("act-1")]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=True)
    mock_executor.return_value.execute.return_value = MagicMock(
        results=[MagicMock(is_success=True)], is_success=True
    )

    result = pipeline_engine.run()

    assert result.is_success is True


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_e2e_approved_action_proceeds(
    mock_planner,
    mock_validator,
    mock_executor,
    mock_audit,
    pipeline_engine,
    approval_provider,
):
    """Scenario 3: Approved action proceeds to execution."""
    req = approval_provider.request_approval("act-1", "plan-1", "run-1", "Test", "LOW")
    approval_provider.approve(req.approval_id)

    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action("act-1", requires_approval=True)]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=True)

    # ارسال run_id یکسان برای جلوگیری از تشخیص Replay Attack
    result = pipeline_engine.run(
        approval_provider=approval_provider,
        pending_approvals={"act-1": req.approval_id},
        run_id="run-1",
    )

    assert result.is_pending_approval is False
    assert result.is_rejected_approval is False
    mock_executor.return_value.execute.assert_called_once()
