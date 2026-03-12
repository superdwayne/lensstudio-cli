"""CLI commands for lens build, export, and preview."""

import click

from ..core import project as proj_core
from ..core import lens as lens_core
from ..utils.formatter import success, error, render_detail


def _load_project(ctx):
    path = ctx.obj.get("project_path")
    if not path:
        error("No project specified. Use --project <path>.")
    data = proj_core.load_project(path)
    return data, path


@click.group("lens")
def lens_group():
    """Build, export, and preview lenses."""
    pass


@lens_group.command("build")
@click.option("-o", "--output", required=True, help="Output file path")
@click.option("-t", "--target", default="snapchat", type=click.Choice(["snapchat", "spectacles", "web"]), help="Target platform")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def lens_build(ctx, output, target, json_mode):
    """Build/export a lens from the project."""
    try:
        data, path = _load_project(ctx)
        result = lens_core.build_lens(path, output, target)
        if result.get("success"):
            size = result.get("size", 0)
            size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
            success(
                f"Built lens: {output} ({size_str}) target={target}",
                json_mode=json_mode,
                data=result,
            )
        else:
            error(result.get("error", "Build failed"), json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@lens_group.command("validate")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def lens_validate(ctx, json_mode):
    """Validate the project for lens submission."""
    try:
        data, path = _load_project(ctx)
        result = lens_core.validate_project(data)

        if json_mode:
            from ..utils.formatter import click_echo_json
            click_echo_json(result)
            return

        from rich.console import Console
        console = Console()

        if result["valid"]:
            console.print("[green bold]✓ Project is valid for submission[/green bold]")
        else:
            console.print("[red bold]✗ Project has validation errors[/red bold]")

        if result["errors"]:
            console.print("\n[red]Errors:[/red]")
            for err in result["errors"]:
                console.print(f"  [red]✗[/red] {err}")

        if result["warnings"]:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warn in result["warnings"]:
                console.print(f"  [yellow]⚠[/yellow] {warn}")

        stats = result.get("stats", {})
        console.print(f"\n[dim]Stats: {stats.get('sceneObjects', 0)} objects, "
                      f"{stats.get('assets', 0)} assets, "
                      f"{stats.get('scripts', 0)} scripts, "
                      f"{stats.get('materials', 0)} materials[/dim]")
    except Exception as e:
        error(str(e), json_mode=json_mode)


@lens_group.command("preview")
@click.option("-d", "--device", default="simulator", help="Preview device (simulator, device)")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def lens_preview(ctx, device, json_mode):
    """Launch lens preview."""
    try:
        data, path = _load_project(ctx)
        result = lens_core.preview_lens(path, device)
        if result.get("success"):
            success(f"Launched preview on {device}", json_mode=json_mode, data=result)
        else:
            error(result.get("error", "Preview failed"), json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@lens_group.command("open")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def lens_open(ctx, json_mode):
    """Open the project in Lens Studio GUI."""
    try:
        data, path = _load_project(ctx)
        result = lens_core.open_in_lens_studio(path)
        if result.get("success"):
            success("Opened in Lens Studio", json_mode=json_mode, data=result)
        else:
            error(result.get("error", "Failed to open"), json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@lens_group.command("backend-info")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def lens_backend_info(json_mode):
    """Show Lens Studio backend information."""
    try:
        info = lens_core.get_backend_info()
        render_detail("Lens Studio Backend", info, json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)
