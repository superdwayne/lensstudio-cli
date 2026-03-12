"""Main CLI entry point for cli-anything-lens-studio.

Supports two modes:
1. Subcommand mode: cli-anything-lens-studio <command> [options]
2. REPL mode: cli-anything-lens-studio (no arguments) → interactive session
"""

import sys

import click

from . import __version__
from .commands.project_cmd import project_group
from .commands.scene_cmd import scene_group
from .commands.asset_cmd import asset_group
from .commands.script_cmd import script_group
from .commands.material_cmd import material_group
from .commands.component_cmd import component_group
from .commands.lens_cmd import lens_group
from .commands.template_cmd import template_group


class LensStudioCLI(click.MultiCommand):
    """Custom MultiCommand that falls back to REPL when invoked without arguments."""

    _commands = {
        "project": project_group,
        "scene": scene_group,
        "asset": asset_group,
        "script": script_group,
        "material": material_group,
        "component": component_group,
        "lens": lens_group,
        "template": template_group,
    }

    def list_commands(self, ctx):
        return sorted(self._commands.keys())

    def get_command(self, ctx, cmd_name):
        return self._commands.get(cmd_name)


@click.command(cls=LensStudioCLI, invoke_without_command=True)
@click.option("--project", "-p", "project_path", default=None, help="Project file path (.lsproj)")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON for all commands")
@click.option("--version", is_flag=True, help="Show version")
@click.pass_context
def cli(ctx, project_path, json_mode, version):
    """cli-anything-lens-studio — Agent-native CLI for Snap Lens Studio.

    Run without arguments to enter interactive REPL mode.
    Run with a subcommand for scripting/pipeline use.

    Examples:

      \b
      # Create a new project
      ls-cli project new -n MyLens -t face-effects

      \b
      # Add a scene object
      ls-cli --project MyLens/MyLens.lsproj scene add -n "3D Object"

      \b
      # Build a lens
      ls-cli --project MyLens/MyLens.lsproj lens build -o output.lens

      \b
      # Interactive mode
      ls-cli
    """
    ctx.ensure_object(dict)
    ctx.obj["project_path"] = project_path
    ctx.obj["json_mode"] = json_mode

    if version:
        if json_mode:
            import json
            print(json.dumps({"version": __version__, "name": "cli-anything-lens-studio"}))
        else:
            click.echo(f"cli-anything-lens-studio v{__version__}")
        return

    # If no subcommand was invoked, start REPL
    if ctx.invoked_subcommand is None:
        _start_repl(project_path)


def _start_repl(project_path=None):
    """Launch the interactive REPL session."""
    from .utils.repl_skin import ReplSession

    def invoke_command(args):
        """Invoke a CLI command from REPL input."""
        try:
            cli.main(args, standalone_mode=False)
        except click.exceptions.UsageError as e:
            from rich.console import Console
            Console(stderr=True).print(f"[red]Usage error:[/red] {e}")
        except SystemExit:
            pass

    session = ReplSession(invoke_command, project_path)

    # If a project was specified, set it as active
    if project_path:
        try:
            from .core.project import load_project
            data = load_project(project_path)
            session.set_project(data["project"]["name"], project_path)
        except Exception:
            pass

    session.run()


def main():
    """Entry point for the CLI."""
    # If no arguments provided (just the command itself), enter REPL
    cli(obj={})


if __name__ == "__main__":
    main()
