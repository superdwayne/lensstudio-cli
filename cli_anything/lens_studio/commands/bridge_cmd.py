"""CLI commands for the bridge layer — install, status, send, logs."""

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
                console.print(f"  [bold]{k}:[/bold] {v}")
        else:
            from ..utils.formatter import error_console

            error_console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")


@click.group("bridge")
def bridge_group():
    """Manage the Lens Studio bridge plugin for live editor communication."""


@bridge_group.command("install")
@click.option("--target", "-t", default=None, help="Override plugin installation directory")
@click.pass_context
def bridge_install(ctx, target):
    """Install the bridge plugin into Lens Studio's plugins directory."""
    from ..bridge.installer import install_plugin

    result = install_plugin(target_dir=target)
    json_mode = ctx.obj.get("json_mode", False) if ctx.obj else False

    if json_mode:
        from ..utils.formatter import click_echo_json

        click_echo_json(result)
    elif result.get("success"):
        from ..utils.formatter import success

        success(f"Plugin installed to {result.get('destination', 'unknown')}")
    else:
        from ..utils.formatter import error

        error(result.get("error", "Installation failed"))


@bridge_group.command("uninstall")
@click.option("--target", "-t", default=None, help="Override plugin directory")
@click.pass_context
def bridge_uninstall(ctx, target):
    """Remove the bridge plugin from Lens Studio."""
    from ..bridge.installer import uninstall_plugin

    result = uninstall_plugin(target_dir=target)
    json_mode = ctx.obj.get("json_mode", False) if ctx.obj else False
    _output(result, json_mode)


@bridge_group.command("status")
@click.pass_context
def bridge_status(ctx):
    """Check bridge plugin connection status and heartbeat."""
    from ..bridge.client import get_bridge_client

    client = get_bridge_client()
    alive = client.is_alive()
    heartbeat = client.get_heartbeat()

    result = {
        "connected": alive,
        "bridge_dir": str(client.bridge_dir),
    }
    if heartbeat:
        result["plugin_version"] = heartbeat.get("plugin_version", "unknown")
        result["ls_version"] = heartbeat.get("ls_version", "unknown")
        result["last_heartbeat"] = heartbeat.get("timestamp", "unknown")

    json_mode = ctx.obj.get("json_mode", False) if ctx.obj else False

    if json_mode:
        from ..utils.formatter import click_echo_json

        click_echo_json(result)
    else:
        from ..utils.formatter import render_detail

        status_label = "[green]Connected[/green]" if alive else "[red]Disconnected[/red]"
        result["status"] = status_label
        render_detail("Bridge Status", result)


@bridge_group.command("send")
@click.argument("domain")
@click.argument("action")
@click.option("--params", "-p", default="{}", help="JSON parameters")
@click.option("--timeout", "-T", default=10.0, type=float, help="Timeout in seconds")
@click.pass_context
def bridge_send(ctx, domain, action, params, timeout):
    """Send a command to the bridge plugin.

    Example: ls-cli bridge send scene add --params '{"name":"MyObject"}'
    """
    try:
        parsed_params = json.loads(params)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON params: {e}", err=True)
        return

    from ..bridge.client import get_bridge_client

    client = get_bridge_client()
    try:
        response = client.send(domain=domain, action=action, params=parsed_params, timeout=timeout)
        result = response.to_dict()
    except Exception as e:
        result = {"success": False, "error": str(e)}

    json_mode = ctx.obj.get("json_mode", False) if ctx.obj else False
    _output(result, json_mode)


@bridge_group.command("cleanup")
@click.option("--max-age", default=300.0, type=float, help="Max age in seconds for stale files")
@click.pass_context
def bridge_cleanup(ctx, max_age):
    """Remove stale command/response files."""
    from ..bridge.client import get_bridge_client

    client = get_bridge_client()
    result = client.cleanup_stale(max_age=max_age)
    result["success"] = True

    json_mode = ctx.obj.get("json_mode", False) if ctx.obj else False
    _output(result, json_mode)


@bridge_group.command("doctor")
@click.pass_context
def bridge_doctor(ctx):
    """Run diagnostic checks on the bridge plugin setup."""
    import subprocess

    from ..bridge.client import get_bridge_client
    from ..bridge.installer import is_installed

    json_mode = ctx.obj.get("json_mode", False) if ctx.obj else False
    checks: list[dict] = []

    # 1. Plugin installed?
    installed = is_installed()
    checks.append({
        "check": "Plugin installed",
        "passed": installed,
        "detail": "Found in Lens Studio plugins directory"
        if installed else "Not installed — run 'ls-cli bridge install'",
    })

    # 2. Lens Studio running?
    ls_running = False
    try:
        result = subprocess.run(
            ["/usr/bin/pgrep", "-x", "Lens Studio"],
            capture_output=True,
            timeout=5,
        )
        ls_running = result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    checks.append({
        "check": "Lens Studio running",
        "passed": ls_running,
        "detail": "Process found" if ls_running else "Lens Studio is not running",
    })

    # 3. Heartbeat fresh?
    client = get_bridge_client()
    heartbeat = client.get_heartbeat()
    alive = client.is_alive()
    checks.append({
        "check": "Heartbeat fresh",
        "passed": alive,
        "detail": f"Last: {heartbeat.get('timestamp', 'unknown')}" if heartbeat else "No heartbeat file found",
    })

    # 4. Plugin version
    plugin_version = heartbeat.get("plugin_version", "unknown") if heartbeat else "unknown"
    checks.append({
        "check": "Plugin version",
        "passed": plugin_version != "unknown",
        "detail": plugin_version,
    })

    # 5. Capabilities reported?
    capabilities = heartbeat.get("capabilities", {}) if heartbeat else {}
    caps_ok = len(capabilities) > 0
    checks.append({
        "check": "Capabilities reported",
        "passed": caps_ok,
        "detail": f"{len(capabilities)} capabilities probed" if caps_ok else "No capabilities data",
    })

    # 6. Ping test (only if heartbeat is alive)
    ping_ok = False
    if alive:
        try:
            resp = client.send(domain="query", action="ping", timeout=5.0)
            ping_ok = resp.success and (resp.data or {}).get("pong", False)
        except Exception:
            logger.debug("Ping failed during doctor check")
    checks.append({
        "check": "Ping responds",
        "passed": ping_ok,
        "detail": "pong received" if ping_ok else "No response" if alive else "Skipped (not alive)",
    })

    if json_mode:
        from ..utils.formatter import click_echo_json

        click_echo_json({"checks": checks, "all_passed": all(c["passed"] for c in checks)})
    else:
        from ..utils.formatter import console

        console.print("\n[bold]Bridge Doctor[/bold]\n")
        for c in checks:
            icon = "[green]PASS[/green]" if c["passed"] else "[red]FAIL[/red]"
            console.print(f"  {icon}  {c['check']}: {c['detail']}")
        console.print()
