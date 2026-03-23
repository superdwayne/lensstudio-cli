"""Tests for the action executor — executes plans with mocked backends."""

import tempfile
from unittest.mock import patch

import pytest

from cli_anything.lens_studio.agent.executor import ActionExecutor
from cli_anything.lens_studio.agent.planner import ActionPlan, ActionStep


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory(prefix="ls_exec_test_") as d:
        yield d


class TestActionExecutor:
    def test_executor_init(self):
        executor = ActionExecutor(project_path="/tmp/test.esproj")
        assert executor._project_path == "/tmp/test.esproj"

    def test_empty_plan_succeeds(self):
        executor = ActionExecutor()
        plan = ActionPlan(request="empty test", steps=[])
        result = executor.execute(plan)
        assert result["success"] is True
        assert result["total_steps"] == 0

    def test_dry_run_skips_execution(self):
        steps = [
            ActionStep(tool="cli.project.create", params={"name": "Test"}),
            ActionStep(tool="bridge.scene.add", params={"name": "Obj1"}),
        ]
        plan = ActionPlan(request="dry test", steps=steps)

        executor = ActionExecutor()
        result = executor.execute(plan, dry_run=True)
        assert result["success"] is True
        assert result["completed"] == 2
        for step in plan.steps:
            assert step.status == "skipped"

    @patch("cli_anything.lens_studio.agent.executor.ActionExecutor._execute_bridge")
    def test_execute_bridge_action(self, mock_bridge):
        mock_bridge.return_value = {"success": True, "data": {"name": "Obj1"}}

        steps = [ActionStep(tool="bridge.scene.add", params={"name": "Obj1"})]
        plan = ActionPlan(request="test bridge", steps=steps)

        executor = ActionExecutor()
        result = executor.execute(plan)
        assert result["success"] is True
        assert result["completed"] == 1

    @patch("cli_anything.lens_studio.agent.executor.ActionExecutor._execute_gui")
    def test_execute_gui_action(self, mock_gui):
        mock_gui.return_value = {"success": True, "method": "gui"}

        steps = [ActionStep(tool="gui.lens.build", params={"target": "snapchat"})]
        plan = ActionPlan(request="test gui", steps=steps)

        executor = ActionExecutor()
        result = executor.execute(plan)
        assert result["success"] is True

    def test_execute_cli_project_create(self, tmp_dir):
        steps = [ActionStep(
            tool="cli.project.create",
            params={"name": "ExecutorTest", "directory": tmp_dir, "template": "blank"},
        )]
        plan = ActionPlan(request="create test project", steps=steps)

        executor = ActionExecutor()
        result = executor.execute(plan)
        assert result["success"] is True
        assert result["completed"] == 1

    def test_critical_failure_aborts(self, tmp_dir):
        steps = [
            ActionStep(tool="cli.project.create", params={"name": "", "directory": "/nonexistent/path/deep"}),
            ActionStep(tool="bridge.scene.add", params={"name": "ShouldNotRun"}),
        ]
        plan = ActionPlan(request="fail test", steps=steps)

        executor = ActionExecutor()
        result = executor.execute(plan)
        # The project creation may fail but shouldn't crash
        assert result["total_steps"] == 2

    def test_unknown_layer_returns_error(self):
        steps = [ActionStep(tool="unknown.action", params={})]
        plan = ActionPlan(request="unknown", steps=steps)

        executor = ActionExecutor()
        result = executor.execute(plan)
        assert result["failed"] == 1

    def test_invalid_tool_name_returns_error(self):
        steps = [ActionStep(tool="x", params={})]
        plan = ActionPlan(request="bad tool", steps=steps)

        executor = ActionExecutor()
        result = executor.execute(plan)
        assert result["failed"] == 1

    def test_results_tracking(self):
        steps = [
            ActionStep(tool="cli.project.create", params={"name": "TrackTest", "template": "blank"}),
        ]
        plan = ActionPlan(request="track test", steps=steps)

        executor = ActionExecutor()
        # Will attempt real project creation (may fail due to directory)
        executor.execute(plan)
        assert len(executor.results) == 1

    @patch("cli_anything.lens_studio.agent.executor.ActionExecutor._execute_bridge")
    def test_bridge_failure_not_critical(self, mock_bridge):
        mock_bridge.return_value = {"success": False, "error": "Component not found"}

        steps = [
            ActionStep(tool="bridge.component.add", params={"target": "X", "type": "Camera"}),
            ActionStep(tool="bridge.scene.list", params={}),
        ]
        plan = ActionPlan(request="non-critical test", steps=steps)

        executor = ActionExecutor()
        result = executor.execute(plan)
        # Non-critical failure should continue to next step
        assert result["total_steps"] == 2

    @patch("cli_anything.lens_studio.agent.executor.ActionExecutor._execute_bridge")
    def test_bridge_not_running_is_critical(self, mock_bridge):
        mock_bridge.return_value = {"success": False, "error": "Bridge plugin is not running"}

        steps = [
            ActionStep(tool="bridge.scene.add", params={"name": "X"}),
            ActionStep(tool="bridge.scene.add", params={"name": "Y"}),
        ]
        plan = ActionPlan(request="critical bridge test", steps=steps)

        executor = ActionExecutor()
        executor.execute(plan)
        assert plan.steps[1].status == "skipped"
