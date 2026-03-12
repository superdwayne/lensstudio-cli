"""CLI commands for script management."""

import click

from ..core import project as proj_core
from ..core import script as script_core
from ..utils.formatter import success, error, render_table, render_detail


def _load_project(ctx):
    path = ctx.obj.get("project_path")
    if not path:
        error("No project specified. Use --project <path>.")
    from pathlib import Path
    data = proj_core.load_project(path)
    project_dir = str(Path(path).parent)
    return data, project_dir, path


@click.group("script")
def script_group():
    """Script management (JavaScript/TypeScript)."""
    pass


@script_group.command("create")
@click.option("-n", "--name", required=True, help="Script name")
@click.option("-t", "--template", default="blank", help="Script template (blank, update, tap, tween, behavior, typescript)")
@click.option("-l", "--language", default="javascript", type=click.Choice(["javascript", "typescript"]), help="Script language")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def script_create(ctx, name, template, language, json_mode):
    """Create a new script file."""
    try:
        data, project_dir, path = _load_project(ctx)
        result = script_core.create_script(data, project_dir, name, template, language=language)
        proj_core.save_project(path, data)
        success(
            f"Created {language} script: {result['fileName']}",
            json_mode=json_mode,
            data=result,
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@script_group.command("list")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def script_list(ctx, json_mode):
    """List all scripts in the project."""
    try:
        data, project_dir, path = _load_project(ctx)
        scripts = script_core.list_scripts(data)

        if not scripts:
            success("No scripts found", json_mode=json_mode, data={"scripts": []})
            return

        rows = []
        for s in scripts:
            rows.append([
                s.get("name", "?"),
                s.get("language", "?"),
                s.get("template", "?"),
                s.get("fileName", "?"),
                s.get("id", "?")[:8],
            ])

        render_table(
            "Project Scripts",
            ["Name", "Language", "Template", "File", "ID"],
            rows,
            json_mode=json_mode,
            json_key="scripts",
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@script_group.command("read")
@click.argument("script_id")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def script_read(ctx, script_id, json_mode):
    """Read the content of a script file."""
    try:
        data, project_dir, path = _load_project(ctx)
        entry = script_core.get_script(data, script_id)
        if not entry:
            entry = script_core.get_script_by_name(data, script_id)
        if not entry:
            error(f"Script not found: {script_id}", json_mode=json_mode)

        content = script_core.read_script_content(project_dir, entry)

        if json_mode:
            from ..utils.formatter import click_echo_json
            click_echo_json({"name": entry["name"], "content": content})
        else:
            from rich.console import Console
            from rich.syntax import Syntax
            console = Console()
            lang = "typescript" if entry.get("language") == "typescript" else "javascript"
            syntax = Syntax(content, lang, theme="monokai", line_numbers=True)
            console.print(syntax)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@script_group.command("write")
@click.argument("script_id")
@click.option("-c", "--content", required=True, help="New script content")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def script_write(ctx, script_id, content, json_mode):
    """Write content to a script file."""
    try:
        data, project_dir, path = _load_project(ctx)
        entry = script_core.get_script(data, script_id)
        if not entry:
            entry = script_core.get_script_by_name(data, script_id)
        if not entry:
            error(f"Script not found: {script_id}", json_mode=json_mode)

        script_core.write_script_content(project_dir, entry, content)
        success(f"Updated script: {entry['name']}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@script_group.command("remove")
@click.argument("script_id")
@click.option("--keep-file", is_flag=True, help="Keep the file on disk")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def script_remove(ctx, script_id, keep_file, json_mode):
    """Remove a script from the project."""
    try:
        data, project_dir, path = _load_project(ctx)
        script_core.remove_script(data, project_dir, script_id, delete_file=not keep_file)
        proj_core.save_project(path, data)
        success(f"Removed script: {script_id}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@script_group.command("attach")
@click.option("--script", "script_id", required=True, help="Script ID or name")
@click.option("--to", "object_id", required=True, help="Scene object ID or name")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def script_attach(ctx, script_id, object_id, json_mode):
    """Attach a script to a scene object."""
    try:
        data, project_dir, path = _load_project(ctx)

        # Resolve script by name if needed
        entry = script_core.get_script(data, script_id)
        if not entry:
            entry = script_core.get_script_by_name(data, script_id)
        if not entry:
            error(f"Script not found: {script_id}", json_mode=json_mode)

        script_core.attach_script(data, object_id, entry["id"])
        proj_core.save_project(path, data)
        success(
            f"Attached {entry['name']} → {object_id}",
            json_mode=json_mode,
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@script_group.command("detach")
@click.option("--script", "script_id", required=True, help="Script ID")
@click.option("--from", "object_id", required=True, help="Scene object ID")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def script_detach(ctx, script_id, object_id, json_mode):
    """Detach a script from a scene object."""
    try:
        data, project_dir, path = _load_project(ctx)
        script_core.detach_script(data, object_id, script_id)
        proj_core.save_project(path, data)
        success(f"Detached script from {object_id}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@script_group.command("templates")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def script_templates(json_mode):
    """List available script templates."""
    rows = []
    for name in script_core.SCRIPT_TEMPLATES:
        rows.append([name])

    render_table(
        "Script Templates",
        ["Template"],
        rows,
        json_mode=json_mode,
        json_key="templates",
    )
