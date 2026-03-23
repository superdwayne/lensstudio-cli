"""AI planner — converts natural language to an ActionPlan via LLM tool use.

Supports multiple providers:
  - anthropic: Anthropic API (Claude models) — requires ANTHROPIC_API_KEY
  - ollama: Local Ollama instance (OpenAI-compatible) — requires running Ollama server
  - openai: OpenAI API — requires OPENAI_API_KEY
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from ..exceptions import AgentPlanningError
from ..utils.logging import get_logger
from .capabilities import ActionRegistry
from .prompts import SYSTEM_PROMPT, format_examples_for_prompt

logger = get_logger(__name__)

# Provider detection: model prefix -> provider
_PROVIDER_PREFIXES = {
    "claude-": "anthropic",
    "ollama:": "ollama",
    "gpt-": "openai",
    "o1": "openai",
    "o3": "openai",
    "o4": "openai",
}

# Default Ollama endpoint
_OLLAMA_BASE_URL = "http://localhost:11434/v1"


def detect_provider(model: str) -> str:
    """Detect the LLM provider from the model name."""
    for prefix, provider in _PROVIDER_PREFIXES.items():
        if model.startswith(prefix):
            return provider
    # Fallback: if it contains a slash it's likely an ollama model (org/model)
    if "/" in model:
        return "ollama"
    return "anthropic"


def strip_provider_prefix(model: str) -> str:
    """Remove the provider prefix (e.g. 'ollama:llama3' -> 'llama3')."""
    if model.startswith("ollama:"):
        return model[7:]
    return model


@dataclass
class ActionStep:
    """A single step in an action plan."""

    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    result: Optional[dict] = None
    status: str = "pending"  # pending, running, success, failed, skipped


@dataclass
class ActionPlan:
    """A sequence of steps to execute."""

    request: str
    steps: list[ActionStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status in ("success", "skipped"))

    @property
    def failed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == "failed")

    def to_dict(self) -> dict:
        return {
            "request": self.request,
            "steps": [
                {
                    "tool": s.tool,
                    "params": s.params,
                    "description": s.description,
                    "status": s.status,
                }
                for s in self.steps
            ],
            "metadata": self.metadata,
        }


def _anthropic_tool_schemas(registry: ActionRegistry) -> list[dict]:
    """Convert registry to Anthropic tool-use format."""
    return registry.to_tool_schemas()


def _openai_tool_schemas(registry: ActionRegistry) -> list[dict]:
    """Convert registry to OpenAI/Ollama function-calling format."""
    tools = []
    for schema in registry.to_tool_schemas():
        tools.append({
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["input_schema"],
            },
        })
    return tools


class ActionPlanner:
    """Plans action sequences from natural language using an LLM.

    Supports Anthropic (Claude), Ollama (local), and OpenAI providers.
    Provider is auto-detected from the model name:
      - claude-*        -> Anthropic API
      - ollama:<model>  -> Ollama (local)
      - org/model       -> Ollama (local)
      - gpt-*           -> OpenAI API
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self._api_key = api_key
        self._model = strip_provider_prefix(model)
        self._provider = provider or detect_provider(model)
        self._base_url = base_url
        self._registry = ActionRegistry()
        self._client = None

    @property
    def registry(self) -> ActionRegistry:
        return self._registry

    def _get_anthropic_client(self):
        """Initialize the Anthropic client."""
        try:
            import anthropic
        except ImportError as e:
            raise AgentPlanningError(
                "anthropic SDK not installed. Run: pip install 'cli-anything-lens-studio[agent]'"
            ) from e

        import os

        api_key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise AgentPlanningError(
                "ANTHROPIC_API_KEY not set. Provide via --api-key or environment variable."
            )

        self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _get_openai_client(self):
        """Initialize an OpenAI-compatible client (works for Ollama and OpenAI)."""
        try:
            from openai import OpenAI
        except ImportError as e:
            raise AgentPlanningError(
                "openai SDK not installed. Run: pip install openai"
            ) from e

        import os

        if self._provider == "ollama":
            base_url = self._base_url or os.environ.get("OLLAMA_BASE_URL", _OLLAMA_BASE_URL)
            # Ollama doesn't need a real API key
            self._client = OpenAI(base_url=base_url, api_key="ollama")
        else:
            api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise AgentPlanningError(
                    "OPENAI_API_KEY not set. Provide via --api-key or environment variable."
                )
            base_url = self._base_url or None
            self._client = OpenAI(api_key=api_key, base_url=base_url)

        return self._client

    def _get_client(self):
        """Lazily initialize the appropriate client."""
        if self._client is not None:
            return self._client

        if self._provider == "anthropic":
            return self._get_anthropic_client()
        else:
            return self._get_openai_client()

    def plan(
        self,
        request: str,
        context: Optional[dict] = None,
    ) -> ActionPlan:
        """Generate an action plan from a natural language request."""
        logger.info("Planning: %s (provider=%s, model=%s)", request, self._provider, self._model)

        client = self._get_client()

        system = SYSTEM_PROMPT + format_examples_for_prompt()
        if context:
            system += f"\n\n## Current Context\n{json.dumps(context, indent=2)}"

        if self._provider == "anthropic":
            return self._plan_anthropic(client, system, request)
        else:
            return self._plan_openai(client, system, request)

    def _plan_anthropic(self, client, system: str, request: str) -> ActionPlan:
        """Plan using the Anthropic API."""
        tools = _anthropic_tool_schemas(self._registry)
        messages = [{"role": "user", "content": request}]

        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system,
                tools=tools,
                messages=messages,
            )
        except Exception as e:
            raise AgentPlanningError(f"Anthropic API call failed: {e}") from e

        steps: list[ActionStep] = []
        for block in response.content:
            if block.type == "tool_use":
                steps.append(ActionStep(
                    tool=block.name,
                    params=block.input or {},
                    description=f"Step {len(steps) + 1}: {block.name}",
                ))

        if not steps:
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            if text_blocks:
                logger.info("LLM returned text instead of tool calls: %s", text_blocks[0][:200])
            raise AgentPlanningError(
                "LLM did not produce any action steps. Try rephrasing your request."
            )

        return self._build_plan(request, steps)

    def _plan_openai(self, client, system: str, request: str) -> ActionPlan:
        """Plan using the OpenAI-compatible API (Ollama, OpenAI, etc.)."""
        tools = _openai_tool_schemas(self._registry)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": request},
        ]

        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tools if tools else None,
                temperature=0.2,
            )
        except Exception as e:
            raise AgentPlanningError(f"LLM API call failed ({self._provider}): {e}") from e

        steps: list[ActionStep] = []
        choice = response.choices[0] if response.choices else None
        if choice and choice.message and choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                fn = tc.function
                try:
                    params = json.loads(fn.arguments) if fn.arguments else {}
                except json.JSONDecodeError:
                    params = {}
                steps.append(ActionStep(
                    tool=fn.name,
                    params=params,
                    description=f"Step {len(steps) + 1}: {fn.name}",
                ))

        if not steps:
            # Check if model returned text instead
            text = ""
            if choice and choice.message and choice.message.content:
                text = choice.message.content[:200]
                logger.info("LLM returned text instead of tool calls: %s", text)
            raise AgentPlanningError(
                "LLM did not produce any action steps. "
                "The model may not support tool calling. Try a different model."
            )

        return self._build_plan(request, steps)

    def _build_plan(self, request: str, steps: list[ActionStep]) -> ActionPlan:
        """Build an ActionPlan from extracted steps."""
        plan = ActionPlan(
            request=request,
            steps=steps,
            metadata={
                "provider": self._provider,
                "model": self._model,
                "tool_count": len(self._registry.actions),
                "step_count": len(steps),
            },
        )
        logger.info("Plan generated: %d steps", len(steps))
        return plan

    def plan_dry(self, request: str, context: Optional[dict] = None) -> ActionPlan:
        """Generate a plan without calling the LLM (returns empty plan for testing)."""
        return ActionPlan(
            request=request,
            steps=[],
            metadata={"dry_run": True},
        )
