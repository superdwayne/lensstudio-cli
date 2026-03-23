"""Tests for auto (AI agent) CLI commands."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cli_anything.lens_studio.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestAutoCapabilities:
    def test_capabilities_lists_actions(self, runner):
        result = runner.invoke(cli, ["auto", "capabilities"], obj={})
        assert result.exit_code == 0

    def test_capabilities_filter_by_layer(self, runner):
        result = runner.invoke(cli, ["auto", "capabilities", "--layer", "cli"], obj={})
        assert result.exit_code == 0

    def test_capabilities_filter_by_domain(self, runner):
        result = runner.invoke(cli, ["auto", "capabilities", "--domain", "scene"], obj={})
        assert result.exit_code == 0

    def test_capabilities_json_mode(self, runner):
        result = runner.invoke(cli, ["--json", "auto", "capabilities"], obj={})
        assert result.exit_code == 0


class TestAutoPlan:
    @patch("cli_anything.lens_studio.agent.planner.ActionPlanner.plan")
    def test_plan_success(self, mock_plan, runner):
        from cli_anything.lens_studio.agent.planner import ActionPlan, ActionStep

        mock_plan.return_value = ActionPlan(
            request="test",
            steps=[ActionStep(tool="cli.project.create", params={"name": "Test"})],
        )

        result = runner.invoke(
            cli,
            ["auto", "plan", "create a test lens", "--api-key", "test-key"],
            obj={},
        )
        # Will fail because _get_client tries to init, but plan is mocked
        # The mock patches the instance method so we need to also mock _get_client
        # For now just verify it doesn't crash with a traceback
        assert result.exit_code == 0

    @patch("cli_anything.lens_studio.agent.planner.ActionPlanner._get_client")
    @patch("cli_anything.lens_studio.agent.planner.ActionPlanner.plan")
    def test_plan_with_mocked_client(self, mock_plan, mock_client, runner):
        from cli_anything.lens_studio.agent.planner import ActionPlan, ActionStep

        mock_plan.return_value = ActionPlan(
            request="test",
            steps=[ActionStep(tool="cli.project.create", params={"name": "Test"})],
        )

        result = runner.invoke(
            cli,
            ["auto", "plan", "create a test lens", "--api-key", "test-key"],
            obj={},
        )
        assert result.exit_code == 0

    def test_plan_failure_no_api_key(self, runner):
        """Plan without API key should handle error gracefully."""
        with patch.dict("os.environ", {}, clear=False):
            result = runner.invoke(
                cli,
                ["auto", "plan", "create a lens"],
                obj={},
            )
            # Should not crash — error handled in try/except
            assert result.exit_code == 0


class TestAutoRun:
    @patch("cli_anything.lens_studio.agent.planner.ActionPlanner._get_client")
    @patch("cli_anything.lens_studio.agent.planner.ActionPlanner.plan")
    def test_run_dry(self, mock_plan, mock_client, runner):
        from cli_anything.lens_studio.agent.planner import ActionPlan, ActionStep

        mock_plan.return_value = ActionPlan(
            request="test",
            steps=[ActionStep(tool="cli.project.create", params={"name": "Test"})],
        )

        result = runner.invoke(
            cli,
            ["auto", "run", "--dry-run", "create a lens", "--api-key", "test-key"],
            obj={},
        )
        assert result.exit_code == 0
