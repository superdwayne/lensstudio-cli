"""CLI commands for the AI planning agent — plan, run, capabilities."""

import json

import click

from ..utils.logging import get_logger

logger = get_logger(__name__)


def _output(result: dict, json_mode: bool):
    """Output a result dict as JSON or human-readable."""
    if json_mode:
        from ..utils.formatter import click_echo_json

        click_echo_json(result)
    else:
        from ..utils.formatter import console

        if result.get("success", True):
            for k, v in result.items():
                if k == "success":
                    continue
                if isinstance(v, (dict, list)):
                    console.print(f"  [bold]{k}:[/bold]")
                    console.print_json(json.dumps(v, default=str))
                else:
                    console.print(f"  [bold]{k}:[/bold] {v}")
        else:
            from ..utils.formatter import error_console

            error_console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")


@click.group("auto")
def auto_group():
    """AI-powered autonomous Lens Studio automation."""


@auto_group.command("plan")
@click.argument("request")
@click.option("--api-key", default=None, help="API key (or set ANTHROPIC_API_KEY / OPENAI_API_KEY)")
@click.option("--model", "-m", default="claude-sonnet-4-5-20250929", help="Model name (prefix with ollama: for local models)")
@click.option("--provider", "-p", default=None, type=click.Choice(["anthropic", "ollama", "openai"]), help="LLM provider (auto-detected from model name)")
@click.option("--base-url", default=None, help="Custom API base URL (e.g. http://localhost:11434/v1)")
@click.pass_context
def auto_plan(ctx, request, api_key, model, provider, base_url):
    """Generate an action plan from a natural language request (without executing).

    Examples:

      ls-cli auto plan "create a face effects lens" --model ollama:llama3.1

      ls-cli auto plan "add a 3D cube to the scene" --model claude-sonnet-4-5-20250929
    """
    from ..agent.planner import ActionPlanner

    json_mode = ctx.obj.get("json_mode", False) if ctx.obj else False
    project_path = ctx.obj.get("project_path") if ctx.obj else None

    try:
        planner = ActionPlanner(api_key=api_key, model=model, provider=provider, base_url=base_url)
        context = _build_context(project_path)
        plan = planner.plan(request, context=context)
        result = {"success": True, "plan": plan.to_dict()}
    except Exception as e:
        result = {"success": False, "error": str(e)}

    _output(result, json_mode)


@auto_group.command("run")
@click.argument("request")
@click.option("--api-key", default=None, help="API key (or set ANTHROPIC_API_KEY / OPENAI_API_KEY)")
@click.option("--model", "-m", default="claude-sonnet-4-5-20250929", help="Model name (prefix with ollama: for local models)")
@click.option("--provider", "-p", default=None, type=click.Choice(["anthropic", "ollama", "openai"]), help="LLM provider (auto-detected from model name)")
@click.option("--base-url", default=None, help="Custom API base URL (e.g. http://localhost:11434/v1)")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
@click.pass_context
def auto_run(ctx, request, api_key, model, provider, base_url, dry_run):
    """Plan and execute a natural language request autonomously.

    Examples:

      ls-cli auto run "add a 3D cube" --model ollama:llama3.1

      ls-cli auto run "create a face effects lens" --model claude-sonnet-4-5-20250929
    """
    from ..agent.executor import ActionExecutor
    from ..agent.planner import ActionPlanner

    json_mode = ctx.obj.get("json_mode", False) if ctx.obj else False
    project_path = ctx.obj.get("project_path") if ctx.obj else None

    try:
        # Plan
        planner = ActionPlanner(api_key=api_key, model=model, provider=provider, base_url=base_url)
        context = _build_context(project_path)
        plan = planner.plan(request, context=context)

        if not json_mode:
            click.echo(f"\nPlan ({plan.total_steps} steps):")
            for i, step in enumerate(plan.steps, 1):
                params_str = json.dumps(step.params) if step.params else "{}"
                click.echo(f"  {i}. {step.tool}({params_str})")
            click.echo("")

        # Execute
        executor = ActionExecutor(project_path=project_path)
        result = executor.execute(plan, dry_run=dry_run)
    except Exception as e:
        result = {"success": False, "error": str(e)}

    _output(result, json_mode)


@auto_group.command("capabilities")
@click.option("--layer", default=None, help="Filter by layer (cli, bridge, gui)")
@click.option("--domain", default=None, help="Filter by domain (scene, asset, etc.)")
@click.pass_context
def auto_capabilities(ctx, layer, domain):
    """List all available actions the agent can use."""
    from ..agent.capabilities import ActionRegistry

    json_mode = ctx.obj.get("json_mode", False) if ctx.obj else False
    registry = ActionRegistry()

    if layer:
        actions = registry.list_by_layer(layer)
    elif domain:
        actions = registry.list_by_domain(domain)
    else:
        actions = list(registry.actions.values())

    result = {
        "success": True,
        "actions": [
            {
                "name": a.name,
                "layer": a.layer,
                "domain": a.domain,
                "description": a.description,
                "parameters": a.parameters,
                "required": a.required_params,
            }
            for a in actions
        ],
        "count": len(actions),
    }

    _output(result, json_mode)


def _build_context(project_path=None) -> dict:
    """Build context information for the planner."""
    context = {}

    if project_path:
        context["current_project"] = project_path

    # Check bridge status
    try:
        from ..bridge.client import get_bridge_client

        client = get_bridge_client()
        context["bridge_alive"] = client.is_alive()
        heartbeat = client.get_heartbeat()
        if heartbeat:
            context["ls_version"] = heartbeat.get("ls_version", "unknown")
    except Exception:
        context["bridge_alive"] = False

    # Check GUI availability
    try:
        from ..gui.actions import get_gui_status

        context["gui"] = get_gui_status()
    except Exception:
        context["gui"] = {"macos": False}

    return context
