"""Action executor — runs plan steps sequentially with validation and error handling."""

import json
import time
from pathlib import Path
from typing import Any, Optional

from ..utils.logging import get_logger
from .capabilities import ActionRegistry
from .planner import ActionPlan, ActionStep

logger = get_logger(__name__)

# Common parameter name aliases that LLMs produce.
# Maps alternative names -> canonical names expected by handlers.
_PARAM_ALIASES: dict[str, str] = {
    "target": "object",
    "object_name": "name",
    "objectName": "name",
    "parent_name": "parent",
    "parentName": "parent",
    "new_name": "new_name",
    "material_name": "material",
    "materialName": "material",
    "script_name": "script",
    "scriptName": "script",
    "component_type": "type",
    "componentType": "type",
}


def _normalize_params(params: dict, domain: str, action: str) -> dict:
    """Normalize parameter names that LLMs commonly get wrong.

    Applies alias mapping, but only when the canonical name isn't
    already present (to avoid overwriting explicit values).
    """
    result = dict(params)

    for alias, canonical in _PARAM_ALIASES.items():
        if alias in result and canonical not in result:
            result[canonical] = result.pop(alias)

    # script.attach: LLM often sends "target" meaning the object
    if domain == "script" and action == "attach":
        if "object" not in result and "target" in params:
            result["object"] = params["target"]

    return result


class ActionExecutor:
    """Executes action plans step-by-step with result tracking."""

    def __init__(self, project_path: Optional[str] = None):
        self._project_path = project_path
        self._registry = ActionRegistry()
        self._results: list[dict[str, Any]] = []
        # Track the project created during execution so later steps can reference it
        self._created_project_path: Optional[str] = None

    @property
    def results(self) -> list[dict]:
        return list(self._results)

    def _resolve_project_path(self, raw_path: Optional[str]) -> Optional[str]:
        """Resolve a project path to absolute, checking common locations."""
        if not raw_path:
            return self._created_project_path or self._project_path

        p = Path(raw_path)
        if p.is_absolute() and p.exists():
            return str(p)

        # Try relative to current dir
        if p.exists():
            return str(p.resolve())

        # Try under the default projects directory
        from ..utils.config import get_projects_dir

        projects_dir = get_projects_dir()
        candidate = projects_dir / raw_path
        if candidate.exists():
            return str(candidate)

        # Try just the project name under projects dir
        name = p.parts[0] if p.parts else raw_path
        for ext in [".esproj", ""]:
            candidate = projects_dir / name / (name + ext)
            if candidate.exists():
                return str(candidate)

        # Return created project path as fallback
        return self._created_project_path or raw_path

    def execute(self, plan: ActionPlan, dry_run: bool = False) -> dict[str, Any]:
        """Execute all steps in a plan sequentially.

        Args:
            plan: The ActionPlan to execute
            dry_run: If True, log steps but don't actually execute

        Returns:
            Summary dict with results
        """
        logger.info("Executing plan: %s (%d steps, dry_run=%s)", plan.request, plan.total_steps, dry_run)
        self._results = []
        self._created_project_path = None
        start_time = time.time()

        for i, step in enumerate(plan.steps):
            step_num = i + 1
            logger.info("[%d/%d] %s(%s)", step_num, plan.total_steps, step.tool, json.dumps(step.params))

            if dry_run:
                step.status = "skipped"
                step.result = {"dry_run": True}
                self._results.append({"step": step_num, "tool": step.tool, "status": "skipped"})
                continue

            step.status = "running"
            try:
                result = self._execute_step(step)
                step.result = result
                step.status = "success" if result.get("success", True) else "failed"
                self._results.append({"step": step_num, "tool": step.tool, "status": step.status, "result": result})

                if step.status == "failed":
                    logger.warning("[%d/%d] Step failed: %s", step_num, plan.total_steps, result.get("error"))
                    # Continue with remaining steps unless it's critical
                    if self._is_critical_failure(step, result):
                        logger.error("Critical failure — aborting remaining steps")
                        self._mark_remaining(plan.steps[i + 1:], "skipped")
                        break

            except Exception as e:
                step.status = "failed"
                step.result = {"error": str(e)}
                self._results.append({"step": step_num, "tool": step.tool, "status": "failed", "error": str(e)})
                logger.error("[%d/%d] Exception: %s", step_num, plan.total_steps, e)
                self._mark_remaining(plan.steps[i + 1:], "skipped")
                break

        elapsed = time.time() - start_time
        return {
            "success": plan.failed_steps == 0,
            "request": plan.request,
            "total_steps": plan.total_steps,
            "completed": plan.completed_steps,
            "failed": plan.failed_steps,
            "elapsed_seconds": round(elapsed, 2),
            "results": self._results,
        }

    def _execute_step(self, step: ActionStep) -> dict[str, Any]:
        """Execute a single action step by routing to the appropriate handler."""
        parts = step.tool.split(".")
        if len(parts) < 2:
            return {"success": False, "error": f"Invalid tool name: {step.tool}"}

        layer = parts[0]
        params = dict(step.params)

        # Inject current project path if not specified
        effective_project = self._resolve_project_path(params.get("project"))
        if effective_project and "project" not in params:
            params["project"] = effective_project

        if layer == "cli":
            return self._execute_cli(parts[1:], params)
        elif layer == "bridge":
            return self._execute_bridge(parts[1:], params)
        elif layer == "gui":
            return self._execute_gui(parts[1:], params)
        else:
            return {"success": False, "error": f"Unknown layer: {layer}"}

    def _execute_cli(self, parts: list[str], params: dict) -> dict:
        """Execute a CLI-layer action."""
        domain = parts[0] if parts else ""
        action = parts[1] if len(parts) > 1 else ""

        if domain == "project" and action == "create":
            from ..core.project import create_project

            result = create_project(
                name=params.get("name", "NewProject"),
                directory=params.get("directory"),
                template=params.get("template", "blank"),
            )

            # Track the created project path for later steps
            # create_project returns {"name", "path", "directory", "template", "id"}
            if result.get("path"):
                self._created_project_path = result["path"]
                result["success"] = True
                logger.info("Tracked created project: %s", self._created_project_path)

            return result
        elif domain == "lens" and action == "validate":
            from ..core.lens import validate_project
            from ..core.project import load_project

            project_path = self._resolve_project_path(params.get("project"))
            if not project_path:
                return {"success": False, "error": "No project path specified"}
            data = load_project(project_path)
            return validate_project(data)
        elif domain == "lens" and action == "build":
            from ..core.lens import build_lens

            project_path = self._resolve_project_path(params.get("project")) or ""
            return build_lens(
                project_path=project_path,
                output_path=params.get("output", "output.lens"),
                target=params.get("target", "snapchat"),
            )
        elif domain == "scene" and action == "add":
            from ..core.project import load_project
            from ..core.scene import add_object

            project_path = self._resolve_project_path(params.get("project"))
            if not project_path:
                return {"success": False, "error": "No project path specified"}
            data = load_project(project_path)
            return add_object(data, name=params.get("name", "NewObject"), parent_id=params.get("parent"))
        elif domain == "asset" and action == "import":
            from ..core.asset import import_asset
            from ..core.project import load_project

            project_path = self._resolve_project_path(params.get("project"))
            if not project_path:
                return {"success": False, "error": "No project path specified"}
            data = load_project(project_path)
            return import_asset(data, project_dir=str(project_path), source_path=params.get("path", ""))
        else:
            return {"success": False, "error": f"Unknown CLI action: {domain}.{action}"}

    def _execute_bridge(self, parts: list[str], params: dict) -> dict:
        """Execute a bridge-layer action."""
        domain = parts[0] if parts else ""
        action = parts[1] if len(parts) > 1 else ""

        # Normalize parameter names (LLMs often use aliases)
        params = _normalize_params(params, domain, action)

        # Handle comma-separated components
        if "components" in params and isinstance(params["components"], str):
            params["components"] = [c.strip() for c in params["components"].split(",")]

        try:
            from ..bridge.client import get_bridge_client

            client = get_bridge_client()
            response = client.send(domain=domain, action=action, params=params)
            return {
                "success": response.success,
                "data": response.data,
                "error": response.error,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_gui(self, parts: list[str], params: dict) -> dict:
        """Execute a GUI-layer action."""
        domain = parts[0] if parts else ""
        action = parts[1] if len(parts) > 1 else ""

        try:
            if domain == "lens" and action == "build":
                from ..gui.actions import build_lens_gui

                return build_lens_gui(
                    output_path=params.get("output"),
                    target=params.get("target", "snapchat"),
                )
            elif domain == "lens" and action == "export":
                from ..gui.actions import export_lens_gui

                return export_lens_gui(output_path=params.get("output"))
            elif domain == "project" and action == "open":
                from ..gui.actions import open_project_gui

                return open_project_gui(project_path=params.get("path", ""))
            elif domain == "preview" and action == "start":
                from ..gui.actions import start_preview_gui

                return start_preview_gui(device=params.get("device", "simulator"))
            else:
                return {"success": False, "error": f"Unknown GUI action: {domain}.{action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _is_critical_failure(self, step: ActionStep, result: dict) -> bool:
        """Determine if a failure should abort the remaining plan."""
        # Project creation failure is critical
        if step.tool == "cli.project.create":
            return True
        # Bridge connection failure is critical for bridge steps
        if step.tool.startswith("bridge.") and "not running" in result.get("error", "").lower():
            return True
        return False

    def _mark_remaining(self, steps: list[ActionStep], status: str):
        for s in steps:
            s.status = status
