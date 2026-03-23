"""Tests for the AI planner — mocks the Anthropic API."""

from unittest.mock import MagicMock, patch

import pytest

from cli_anything.lens_studio.agent.capabilities import ActionDef, ActionRegistry
from cli_anything.lens_studio.agent.planner import ActionPlan, ActionPlanner, ActionStep
from cli_anything.lens_studio.agent.prompts import (
    FEW_SHOT_EXAMPLES,
    SYSTEM_PROMPT,
    format_examples_for_prompt,
)
from cli_anything.lens_studio.exceptions import AgentPlanningError


class TestActionStep:
    def test_create_step(self):
        step = ActionStep(tool="bridge.scene.add", params={"name": "Obj1"})
        assert step.tool == "bridge.scene.add"
        assert step.params["name"] == "Obj1"
        assert step.status == "pending"

    def test_step_default_status(self):
        step = ActionStep(tool="cli.project.create")
        assert step.status == "pending"
        assert step.result is None


class TestActionPlan:
    def test_empty_plan(self):
        plan = ActionPlan(request="test")
        assert plan.total_steps == 0
        assert plan.completed_steps == 0
        assert plan.failed_steps == 0

    def test_plan_with_steps(self):
        steps = [
            ActionStep(tool="cli.project.create", status="success"),
            ActionStep(tool="bridge.scene.add", status="success"),
            ActionStep(tool="bridge.component.add", status="failed"),
            ActionStep(tool="cli.lens.validate", status="pending"),
        ]
        plan = ActionPlan(request="test", steps=steps)
        assert plan.total_steps == 4
        assert plan.completed_steps == 2
        assert plan.failed_steps == 1

    def test_to_dict(self):
        plan = ActionPlan(
            request="create lens",
            steps=[ActionStep(tool="cli.project.create", params={"name": "Test"})],
        )
        d = plan.to_dict()
        assert d["request"] == "create lens"
        assert len(d["steps"]) == 1
        assert d["steps"][0]["tool"] == "cli.project.create"


class TestActionRegistry:
    def test_registry_has_actions(self):
        reg = ActionRegistry()
        assert len(reg.actions) > 0

    def test_registry_has_cli_actions(self):
        reg = ActionRegistry()
        cli_actions = reg.list_by_layer("cli")
        assert len(cli_actions) > 0
        assert any(a.name == "cli.project.create" for a in cli_actions)

    def test_registry_has_bridge_actions(self):
        reg = ActionRegistry()
        bridge_actions = reg.list_by_layer("bridge")
        assert len(bridge_actions) > 0
        assert any(a.name == "bridge.scene.add" for a in bridge_actions)

    def test_registry_has_gui_actions(self):
        reg = ActionRegistry()
        gui_actions = reg.list_by_layer("gui")
        assert len(gui_actions) > 0
        assert any(a.name == "gui.lens.build" for a in gui_actions)

    def test_to_tool_schemas(self):
        reg = ActionRegistry()
        schemas = reg.to_tool_schemas()
        assert len(schemas) > 0
        schema = schemas[0]
        assert "name" in schema
        assert "description" in schema
        assert "input_schema" in schema

    def test_get_existing_action(self):
        reg = ActionRegistry()
        action = reg.get("cli.project.create")
        assert action is not None
        assert action.domain == "project"

    def test_get_nonexistent_action(self):
        reg = ActionRegistry()
        assert reg.get("nonexistent") is None

    def test_list_by_domain(self):
        reg = ActionRegistry()
        scene_actions = reg.list_by_domain("scene")
        assert len(scene_actions) > 0
        for a in scene_actions:
            assert a.domain == "scene"

    def test_summary(self):
        reg = ActionRegistry()
        s = reg.summary()
        assert isinstance(s, list)
        assert len(s) > 0
        assert "name" in s[0]
        assert "layer" in s[0]

    def test_register_custom_action(self):
        reg = ActionRegistry()
        custom = ActionDef(
            name="custom.test.action",
            layer="custom",
            domain="test",
            description="A test action",
        )
        reg.register(custom)
        assert reg.get("custom.test.action") is not None


class TestPrompts:
    def test_system_prompt_not_empty(self):
        assert len(SYSTEM_PROMPT) > 100

    def test_few_shot_examples_exist(self):
        assert len(FEW_SHOT_EXAMPLES) > 0

    def test_format_examples(self):
        formatted = format_examples_for_prompt()
        assert "Examples" in formatted
        assert "User:" in formatted


class TestActionPlanner:
    def test_planner_init(self):
        planner = ActionPlanner(api_key="test-key")
        assert planner._model == "claude-sonnet-4-5-20250929"

    def test_planner_no_api_key_raises(self):
        planner = ActionPlanner()
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AgentPlanningError, match="(?i)anthropic"):
                planner._get_client()

    def test_plan_dry(self):
        planner = ActionPlanner(api_key="test")
        plan = planner.plan_dry("create a lens")
        assert plan.request == "create a lens"
        assert plan.metadata["dry_run"] is True

    @patch("cli_anything.lens_studio.agent.planner.ActionPlanner._get_client")
    def test_plan_with_mock_api(self, mock_get_client):
        # Mock Anthropic response with tool_use blocks
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "cli.project.create"
        mock_tool_block.input = {"name": "TestLens"}

        mock_tool_block2 = MagicMock()
        mock_tool_block2.type = "tool_use"
        mock_tool_block2.name = "bridge.scene.add"
        mock_tool_block2.input = {"name": "Tracker"}

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block, mock_tool_block2]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        planner = ActionPlanner(api_key="test")
        plan = planner.plan("create an AR lens")

        assert plan.total_steps == 2
        assert plan.steps[0].tool == "cli.project.create"
        assert plan.steps[1].tool == "bridge.scene.add"

    @patch("cli_anything.lens_studio.agent.planner.ActionPlanner._get_client")
    def test_plan_no_tool_calls_raises(self, mock_get_client):
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "I cannot do that"

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        planner = ActionPlanner(api_key="test")
        with pytest.raises(AgentPlanningError, match="did not produce"):
            planner.plan("do something impossible")
