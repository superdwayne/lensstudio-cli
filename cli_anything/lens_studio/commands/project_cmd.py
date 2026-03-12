"""CLI commands for project management."""

import click

from ..core import project as proj_core
from ..utils.formatter import success, error, render_table, render_detail


@click.group("project")
def project_group():
    """Manage Lens Studio projects."""
    pass


@project_group.command("new")
@click.option("-n", "--name", required=True, help="Project name")
@click.option("-d", "--directory", default=None, help="Parent directory (default: ~/LensStudio/Projects)")
@click.option("-t", "--template", default="blank", help="Template to use (blank, face-effects, world-ar, etc.)")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def project_new(name, directory, template, json_mode):
    """Create a new Lens Studio project."""
    try:
        result = proj_core.create_project(name, directory, template)
        success(
            f"Created {template} project: {result['name']}",
            json_mode=json_mode,
            data=result,
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@project_group.command("info")
@click.argument("path", required=False)
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def project_info(ctx, path, json_mode):
    """Show project information."""
    path = path or ctx.obj.get("project_path")
    if not path:
        error("No project specified. Use --project or provide a path.", json_mode=json_mode)
    try:
        info = proj_core.project_info(path)
        render_detail(
            f"Project: {info['name']}",
            {
                "ID": info["id"],
                "Template": info["template"],
                "Created": info["created"],
                "Modified": info["modified"],
                "Lens Studio": info["lensStudioVersion"],
                "Scene Objects": str(info["sceneObjects"]),
                "Assets": str(info["assets"]),
                "Scripts": str(info["scripts"]),
                "Materials": str(info["materials"]),
                "Platform": info["targetPlatform"],
                "Resolution": f"{info['resolution'].get('width', '?')}x{info['resolution'].get('height', '?')}",
            },
            json_mode=json_mode,
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@project_group.command("list")
@click.option("-d", "--directory", default=None, help="Projects directory")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def project_list(directory, json_mode):
    """List all projects."""
    try:
        projects = proj_core.list_projects(directory)
        if not projects:
            success("No projects found", json_mode=json_mode, data={"projects": []})
            return

        rows = []
        for p in projects:
            rows.append([
                p.get("name", "?"),
                p.get("template", "?"),
                str(p.get("sceneObjects", "?")),
                str(p.get("assets", "?")),
                p.get("modified", "?")[:10] if p.get("modified") else "?",
            ])

        render_table(
            "Lens Studio Projects",
            ["Name", "Template", "Objects", "Assets", "Modified"],
            rows,
            json_mode=json_mode,
            json_key="projects",
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@project_group.command("open")
@click.argument("path", required=False)
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def project_open(ctx, path, json_mode):
    """Open a project in Lens Studio."""
    path = path or ctx.obj.get("project_path")
    if not path:
        error("No project specified.", json_mode=json_mode)
    try:
        from ..core.lens import open_in_lens_studio
        result = open_in_lens_studio(path)
        if result["success"]:
            success(f"Opened project in Lens Studio", json_mode=json_mode, data=result)
        else:
            error(result.get("error", "Failed to open"), json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@project_group.command("delete")
@click.argument("path")
@click.option("--force", is_flag=True, help="Skip confirmation")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def project_delete(path, force, json_mode):
    """Delete a project."""
    if not force and not json_mode:
        if not click.confirm(f"Delete project at {path}?"):
            return
    try:
        proj_core.delete_project(path, force=force)
        success(f"Deleted project: {path}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)
