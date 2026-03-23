"""Tests for bridge protocol — BridgeCommand and BridgeResponse dataclasses."""

import json

from cli_anything.lens_studio.bridge.protocol import (
    BridgeCommand,
    BridgeResponse,
    CommandDomain,
)


class TestCommandDomain:
    def test_domain_values(self):
        assert CommandDomain.SCENE == "scene"
        assert CommandDomain.ASSET == "asset"
        assert CommandDomain.COMPONENT == "component"
        assert CommandDomain.SCRIPT == "script"
        assert CommandDomain.MATERIAL == "material"
        assert CommandDomain.QUERY == "query"

    def test_domain_is_string(self):
        assert isinstance(CommandDomain.SCENE, str)


class TestBridgeCommand:
    def test_create_basic(self):
        cmd = BridgeCommand(domain="scene", action="add")
        assert cmd.domain == "scene"
        assert cmd.action == "add"
        assert cmd.params == {}
        assert cmd.id  # auto-generated UUID
        assert cmd.timestamp  # auto-generated

    def test_create_with_params(self):
        cmd = BridgeCommand(
            domain="scene",
            action="add",
            params={"name": "TestObj", "parent": "Root"},
        )
        assert cmd.params["name"] == "TestObj"
        assert cmd.params["parent"] == "Root"

    def test_to_dict(self):
        cmd = BridgeCommand(domain="asset", action="import", params={"path": "/tmp/tex.png"})
        d = cmd.to_dict()
        assert d["domain"] == "asset"
        assert d["action"] == "import"
        assert d["params"]["path"] == "/tmp/tex.png"
        assert "id" in d
        assert "timestamp" in d

    def test_from_dict(self):
        data = {
            "domain": "component",
            "action": "add",
            "params": {"target": "Obj1", "type": "Camera"},
            "id": "test-uuid-123",
            "timestamp": "2026-01-01T00:00:00",
        }
        cmd = BridgeCommand.from_dict(data)
        assert cmd.domain == "component"
        assert cmd.action == "add"
        assert cmd.id == "test-uuid-123"

    def test_roundtrip(self):
        cmd = BridgeCommand(domain="query", action="ping")
        data = cmd.to_dict()
        cmd2 = BridgeCommand.from_dict(data)
        assert cmd.domain == cmd2.domain
        assert cmd.action == cmd2.action
        assert cmd.id == cmd2.id

    def test_to_dict_is_json_serializable(self):
        cmd = BridgeCommand(domain="scene", action="list", params={"filter": True})
        json_str = json.dumps(cmd.to_dict())
        assert "scene" in json_str

    def test_unique_ids(self):
        cmd1 = BridgeCommand(domain="scene", action="add")
        cmd2 = BridgeCommand(domain="scene", action="add")
        assert cmd1.id != cmd2.id


class TestBridgeResponse:
    def test_success_response(self):
        resp = BridgeResponse(
            command_id="abc-123",
            success=True,
            data={"objects": [{"name": "Obj1"}]},
        )
        assert resp.success is True
        assert resp.data["objects"][0]["name"] == "Obj1"
        assert resp.error is None

    def test_error_response(self):
        resp = BridgeResponse(
            command_id="abc-123",
            success=False,
            error="Object not found",
        )
        assert resp.success is False
        assert resp.error == "Object not found"

    def test_to_dict(self):
        resp = BridgeResponse(command_id="x", success=True, data={"count": 5})
        d = resp.to_dict()
        assert d["command_id"] == "x"
        assert d["success"] is True
        assert d["data"]["count"] == 5

    def test_from_dict(self):
        data = {
            "command_id": "y",
            "success": False,
            "error": "timeout",
            "timestamp": "2026-01-01T00:00:00",
        }
        resp = BridgeResponse.from_dict(data)
        assert resp.command_id == "y"
        assert resp.success is False
        assert resp.error == "timeout"

    def test_roundtrip(self):
        resp = BridgeResponse(command_id="z", success=True, data={"key": "value"})
        data = resp.to_dict()
        resp2 = BridgeResponse.from_dict(data)
        assert resp.command_id == resp2.command_id
        assert resp.data == resp2.data
