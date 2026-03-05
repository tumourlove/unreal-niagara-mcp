"""Tests for the editor bridge module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from unreal_niagara_mcp.editor_bridge import (
    EditorBridge,
    _build_message,
    _parse_message,
    PROTOCOL_MAGIC,
    PROTOCOL_VERSION,
)


class TestBuildMessage:
    """Tests for _build_message."""

    def test_build_message_produces_valid_json(self):
        raw = _build_message("ping", "node-123")
        msg = json.loads(raw)
        assert msg["version"] == PROTOCOL_VERSION
        assert msg["magic"] == PROTOCOL_MAGIC
        assert msg["type"] == "ping"
        assert msg["source"] == "node-123"

    def test_build_message_includes_dest_when_provided(self):
        raw = _build_message("command", "src", dest="dst")
        msg = json.loads(raw)
        assert msg["dest"] == "dst"

    def test_build_message_omits_dest_when_none(self):
        raw = _build_message("ping", "src")
        msg = json.loads(raw)
        assert "dest" not in msg

    def test_build_message_includes_data(self):
        raw = _build_message("command", "src", data={"command": "print(1)"})
        msg = json.loads(raw)
        assert msg["data"]["command"] == "print(1)"


class TestParseMessage:
    """Tests for _parse_message."""

    def test_parse_valid_message(self):
        raw = json.dumps({
            "version": PROTOCOL_VERSION,
            "magic": PROTOCOL_MAGIC,
            "type": "pong",
            "source": "editor-1",
        })
        result = _parse_message(raw)
        assert result is not None
        assert result["type"] == "pong"

    def test_parse_rejects_wrong_magic(self):
        raw = json.dumps({
            "version": PROTOCOL_VERSION,
            "magic": "wrong_magic",
            "type": "pong",
            "source": "editor-1",
        })
        assert _parse_message(raw) is None

    def test_parse_rejects_wrong_version(self):
        raw = json.dumps({
            "version": 999,
            "magic": PROTOCOL_MAGIC,
            "type": "pong",
            "source": "editor-1",
        })
        assert _parse_message(raw) is None

    def test_parse_rejects_invalid_json(self):
        assert _parse_message("not json at all") is None

    def test_parse_rejects_empty_string(self):
        assert _parse_message("") is None


class TestEditorBridge:
    """Tests for EditorBridge."""

    def test_is_editor_running_returns_true_when_found(self):
        bridge = EditorBridge(auto_connect=False)
        mock_result = MagicMock()
        mock_result.stdout = "UnrealEditor.exe            12345 Console  1    500,000 K"
        with patch("unreal_niagara_mcp.editor_bridge.subprocess.run", return_value=mock_result):
            assert bridge.is_editor_running() is True

    def test_is_editor_running_returns_false_when_not_found(self):
        bridge = EditorBridge(auto_connect=False)
        mock_result = MagicMock()
        mock_result.stdout = "INFO: No tasks are running which match the specified criteria."
        with patch("unreal_niagara_mcp.editor_bridge.subprocess.run", return_value=mock_result):
            assert bridge.is_editor_running() is False

    def test_is_editor_running_returns_false_on_error(self):
        bridge = EditorBridge(auto_connect=False)
        with patch("unreal_niagara_mcp.editor_bridge.subprocess.run", side_effect=FileNotFoundError):
            assert bridge.is_editor_running() is False

    def test_is_connected_false_by_default(self):
        bridge = EditorBridge(auto_connect=False)
        assert bridge.is_connected() is False

    def test_disconnect_resets_state(self):
        bridge = EditorBridge(auto_connect=False)
        bridge._connected = True
        bridge._command_socket = MagicMock()
        bridge._remote_node_id = "some-id"
        bridge.disconnect()
        assert bridge.is_connected() is False
        assert bridge._remote_node_id is None
