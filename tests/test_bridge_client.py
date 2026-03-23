"""Tests for the bridge client — file-based IPC with mock filesystem."""

import json
import os
import tempfile
import time

import pytest

from cli_anything.lens_studio.bridge.client import BridgeClient
from cli_anything.lens_studio.bridge.protocol import BridgeCommand
from cli_anything.lens_studio.exceptions import BridgeNotRunningError, BridgeTimeoutError


@pytest.fixture
def bridge_dir():
    with tempfile.TemporaryDirectory(prefix="ls_bridge_test_") as d:
        yield d


@pytest.fixture
def client(bridge_dir):
    return BridgeClient(bridge_dir=bridge_dir)


class TestBridgeClientInit:
    def test_creates_dirs(self, client, bridge_dir):
        assert os.path.isdir(os.path.join(bridge_dir, "commands"))
        assert os.path.isdir(os.path.join(bridge_dir, "responses"))

    def test_bridge_dir_property(self, client, bridge_dir):
        assert str(client.bridge_dir) == bridge_dir


class TestHeartbeat:
    def test_not_alive_without_heartbeat(self, client):
        assert client.is_alive() is False

    def test_alive_with_fresh_heartbeat(self, client, bridge_dir):
        hb_path = os.path.join(bridge_dir, "heartbeat.json")
        with open(hb_path, "w") as f:
            json.dump({"alive": True, "plugin_version": "1.0.0"}, f)
        assert client.is_alive() is True

    def test_stale_heartbeat(self, client, bridge_dir):
        hb_path = os.path.join(bridge_dir, "heartbeat.json")
        with open(hb_path, "w") as f:
            json.dump({"alive": True}, f)
        # Make it old
        old_time = time.time() - 10
        os.utime(hb_path, (old_time, old_time))
        assert client.is_alive() is False

    def test_get_heartbeat_data(self, client, bridge_dir):
        hb_path = os.path.join(bridge_dir, "heartbeat.json")
        with open(hb_path, "w") as f:
            json.dump({"alive": True, "plugin_version": "1.0.0", "ls_version": "5.3.0"}, f)
        data = client.get_heartbeat()
        assert data["plugin_version"] == "1.0.0"
        assert data["ls_version"] == "5.3.0"

    def test_get_heartbeat_missing(self, client):
        assert client.get_heartbeat() is None


class TestSendCommand:
    def test_send_raises_when_not_running(self, client):
        with pytest.raises(BridgeNotRunningError):
            client.send("scene", "list")

    def test_write_command_file(self, client, bridge_dir):
        cmd = BridgeCommand(domain="scene", action="list")
        client._write_command(cmd)

        cmd_file = os.path.join(bridge_dir, "commands", f"cmd-{cmd.id}.json")
        assert os.path.exists(cmd_file)

        with open(cmd_file) as f:
            data = json.load(f)
        assert data["domain"] == "scene"
        assert data["action"] == "list"

    def test_poll_response_found(self, client, bridge_dir):
        cmd_id = "test-poll-123"
        resp_path = os.path.join(bridge_dir, "responses", f"resp-{cmd_id}.json")
        resp_data = {
            "command_id": cmd_id,
            "success": True,
            "data": {"objects": []},
        }
        with open(resp_path, "w") as f:
            json.dump(resp_data, f)

        resp = client._poll_response(cmd_id, timeout=2.0)
        assert resp.success is True
        assert resp.command_id == cmd_id

    def test_poll_response_timeout(self, client):
        with pytest.raises(BridgeTimeoutError):
            client._poll_response("nonexistent", timeout=0.3)

    def test_send_with_mock_heartbeat_and_response(self, client, bridge_dir):
        # Write a fresh heartbeat
        hb_path = os.path.join(bridge_dir, "heartbeat.json")
        with open(hb_path, "w") as f:
            json.dump({"alive": True}, f)

        # Pre-write a response that matches the command we'll send
        # We need to intercept the command ID, so we'll use send_command
        cmd = BridgeCommand(domain="query", action="ping")

        # Pre-write response
        resp_path = os.path.join(bridge_dir, "responses", f"resp-{cmd.id}.json")
        with open(resp_path, "w") as f:
            json.dump({"command_id": cmd.id, "success": True, "data": {"pong": True}}, f)

        resp = client.send_command(cmd, timeout=2.0)
        assert resp.success is True
        assert resp.data["pong"] is True


class TestCleanup:
    def test_cleanup_stale_files(self, client, bridge_dir):
        # Create old files
        cmd_dir = os.path.join(bridge_dir, "commands")
        resp_dir = os.path.join(bridge_dir, "responses")

        for i in range(3):
            cmd_path = os.path.join(cmd_dir, f"cmd-old-{i}.json")
            with open(cmd_path, "w") as f:
                json.dump({"id": f"old-{i}"}, f)
            old_time = time.time() - 600
            os.utime(cmd_path, (old_time, old_time))

        for i in range(2):
            resp_path = os.path.join(resp_dir, f"resp-old-{i}.json")
            with open(resp_path, "w") as f:
                json.dump({"command_id": f"old-{i}"}, f)
            old_time = time.time() - 600
            os.utime(resp_path, (old_time, old_time))

        result = client.cleanup_stale(max_age=300)
        assert result["commands"] == 3
        assert result["responses"] == 2
