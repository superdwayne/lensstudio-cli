"""Tests for bridge CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli_anything.lens_studio.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestBridgeInstall:
    def test_install_with_target(self, runner, tmp_dir):
        from cli_anything.lens_studio.bridge.installer import get_plugin_source_dir

        source = get_plugin_source_dir()
        if source.is_dir():
            result = runner.invoke(cli, ["bridge", "install", "--target", tmp_dir], obj={})
            assert result.exit_code == 0
            assert "installed" in result.output.lower() or "Plugin installed" in result.output


class TestBridgeStatus:
    @patch("cli_anything.lens_studio.bridge.client.get_bridge_client")
    def test_status_no_heartbeat(self, mock_get, runner):
        mock_client = MagicMock()
        mock_client.is_alive.return_value = False
        mock_client.get_heartbeat.return_value = None
        mock_client.bridge_dir = "/tmp/bridge"
        mock_get.return_value = mock_client

        result = runner.invoke(cli, ["bridge", "status"], obj={})
        assert result.exit_code == 0

    @patch("cli_anything.lens_studio.bridge.client.get_bridge_client")
    def test_status_json_mode(self, mock_get, runner):
        mock_client = MagicMock()
        mock_client.is_alive.return_value = True
        mock_client.get_heartbeat.return_value = {
            "plugin_version": "1.0.0",
            "ls_version": "5.3.0",
            "timestamp": "2026-01-01T00:00:00",
        }
        mock_client.bridge_dir = "/tmp/bridge"
        mock_get.return_value = mock_client

        result = runner.invoke(cli, ["--json", "bridge", "status"], obj={})
        assert result.exit_code == 0


class TestBridgeSend:
    def test_send_invalid_json(self, runner):
        result = runner.invoke(
            cli,
            ["bridge", "send", "scene", "list", "--params", "not-json"],
            obj={},
        )
        # Should gracefully handle the bad JSON
        assert "Invalid JSON" in result.output


class TestBridgeCleanup:
    @patch("cli_anything.lens_studio.bridge.client.get_bridge_client")
    def test_cleanup_command(self, mock_get, runner):
        mock_client = MagicMock()
        mock_client.cleanup_stale.return_value = {"commands": 0, "responses": 0}
        mock_get.return_value = mock_client

        result = runner.invoke(cli, ["bridge", "cleanup"], obj={})
        assert result.exit_code == 0
