"""CLI commands for template management."""

import click

from ..core import template as tmpl_core
from ..utils.formatter import success, error, render_table, render_detail


@click.group("template")
def template_group():
    """List and apply project templates."""
    pass


@template_group.command("list")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def template_list(json_mode):
    """List all available templates."""
    templates = tmpl_core.list_templates()
    rows = [[t["name"], t["description"]] for t in templates]
    render_table(
        "Lens Studio Templates",
        ["Name", "Description"],
        rows,
        json_mode=json_mode,
        json_key="templates",
    )


@template_group.command("info")
@click.argument("template_name")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def template_info(template_name, json_mode):
    """Show detailed template information."""
    try:
        info = tmpl_core.template_info(template_name)
        if json_mode:
            from ..utils.formatter import click_echo_json
            click_echo_json(info)
        else:
            fields = {
                "Name": info["name"],
                "Description": info["description"],
                "Difficulty": info.get("difficulty", "?"),
                "Components": ", ".join(info.get("components", [])),
                "Features": ", ".join(info.get("features", [])),
                "Use Cases": ", ".join(info.get("use_cases", [])),
            }
            render_detail(f"Template: {template_name}", fields)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@template_group.command("apply")
@click.option("-n", "--name", required=True, help="New project name")
@click.option("-t", "--template", "template_name", required=True, help="Template to apply")
@click.option("-d", "--directory", default=None, help="Parent directory")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def template_apply(name, template_name, directory, json_mode):
    """Create a new project from a template."""
    try:
        result = tmpl_core.apply_template(name, template_name, directory)
        success(
            f"Created project '{name}' from template '{template_name}'",
            json_mode=json_mode,
            data=result,
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)
