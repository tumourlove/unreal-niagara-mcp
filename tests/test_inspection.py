"""Tests for Niagara inspection tools."""

import json
from unittest.mock import MagicMock, patch

import pytest

from unreal_niagara_mcp.server import _reset_state, mcp


@pytest.fixture(autouse=True)
def reset():
    _reset_state()
    yield
    _reset_state()


def _make_bridge_result(data: dict) -> dict:
    """Create a successful bridge.run_command() return value."""
    return {
        "success": True,
        "output": json.dumps(data),
    }


def _make_error_result(message: str) -> dict:
    """Create a failed bridge.run_command() return value."""
    return {
        "success": True,
        "output": json.dumps({"error": True, "message": message}),
    }


# ---------------------------------------------------------------------------
# get_niagara_system_info
# ---------------------------------------------------------------------------


class TestGetNiagaraSystemInfo:

    def test_returns_formatted_system_info(self):
        from unreal_niagara_mcp.inspection.system_tools import get_niagara_system_info

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitter_count": 3,
            "warmup_time": 1.5,
            "warmup_tick_count": 10,
            "warmup_tick_delta": 0.0333,
            "determinism": True,
            "fixed_tick_delta": False,
            "fixed_tick_delta_time": 0.0167,
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.system_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_system_info("/Game/VFX/NS_Fire")

        assert "Niagara System: /Game/VFX/NS_Fire" in result
        assert "Emitter Count: 3" in result
        assert "Warmup Time: 1.5" in result
        assert "Warmup Tick Count: 10" in result
        assert "Determinism: True" in result
        assert "Fixed Tick Delta: False" in result
        assert "Fixed Tick Delta Time: 0.0167" in result

    def test_handles_asset_not_found(self):
        from unreal_niagara_mcp.inspection.system_tools import get_niagara_system_info

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_error_result(
            "Cannot load asset: /Game/VFX/Missing"
        )

        with patch("unreal_niagara_mcp.inspection.system_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_system_info("/Game/VFX/Missing")

        assert "Error" in result
        assert "Cannot load asset" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.inspection.system_tools import get_niagara_system_info
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.inspection.system_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_system_info("/Game/VFX/NS_Fire")

        assert "Editor not available" in result

    def test_handles_command_failure(self):
        from unreal_niagara_mcp.inspection.system_tools import get_niagara_system_info

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = {
            "success": False,
            "result": "Python error",
        }

        with patch("unreal_niagara_mcp.inspection.system_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_system_info("/Game/VFX/NS_Fire")

        assert "Error" in result


# ---------------------------------------------------------------------------
# get_niagara_emitters
# ---------------------------------------------------------------------------


class TestGetNiagaraEmitters:

    def test_returns_formatted_emitter_list(self):
        from unreal_niagara_mcp.inspection.system_tools import get_niagara_emitters

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [
                {
                    "name": "Flames",
                    "is_enabled": True,
                    "sim_target": "CPUSim",
                    "local_space": False,
                    "bounds_mode": "Auto",
                    "renderer_count": 1,
                },
                {
                    "name": "Sparks",
                    "is_enabled": True,
                    "sim_target": "GPUComputeSim",
                    "local_space": False,
                    "bounds_mode": "Fixed",
                    "renderer_count": 2,
                },
                {
                    "name": "Smoke",
                    "is_enabled": False,
                    "sim_target": "CPUSim",
                    "local_space": True,
                    "bounds_mode": "Dynamic",
                    "renderer_count": 1,
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.system_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_emitters("/Game/VFX/NS_Fire")

        assert "Emitters (3):" in result
        assert "[0] Flames (Enabled)" in result
        assert "[1] Sparks (Enabled)" in result
        assert "[2] Smoke (Disabled)" in result
        assert "Sim Target: GPUComputeSim" in result
        assert "Local Space: True" in result
        assert "Bounds Mode: Fixed" in result
        assert "Renderers: 2" in result

    def test_handles_empty_emitters(self):
        from unreal_niagara_mcp.inspection.system_tools import get_niagara_emitters

        mock_data = {
            "asset_path": "/Game/VFX/NS_Empty",
            "emitters": [],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.system_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_emitters("/Game/VFX/NS_Empty")

        assert "no emitters" in result

    def test_handles_asset_not_found(self):
        from unreal_niagara_mcp.inspection.system_tools import get_niagara_emitters

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_error_result(
            "Cannot load asset: /Game/VFX/Missing"
        )

        with patch("unreal_niagara_mcp.inspection.system_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_emitters("/Game/VFX/Missing")

        assert "Error" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.inspection.system_tools import get_niagara_emitters
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.inspection.system_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_emitters("/Game/VFX/NS_Fire")

        assert "Editor not available" in result

    def test_output_includes_renderer_count(self):
        from unreal_niagara_mcp.inspection.system_tools import get_niagara_emitters

        mock_data = {
            "asset_path": "/Game/VFX/NS_Single",
            "emitters": [
                {
                    "name": "Main",
                    "is_enabled": True,
                    "sim_target": "CPUSim",
                    "local_space": False,
                    "bounds_mode": "Auto",
                    "renderer_count": 3,
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.system_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_emitters("/Game/VFX/NS_Single")

        assert "Renderers: 3" in result


# ---------------------------------------------------------------------------
# Server-level tests
# ---------------------------------------------------------------------------


class TestServerHelpers:

    def test_escape_py_string_handles_backslashes(self):
        from unreal_niagara_mcp.server import _escape_py_string
        assert _escape_py_string('C:\\Game\\Test') == 'C:\\\\Game\\\\Test'

    def test_escape_py_string_handles_quotes(self):
        from unreal_niagara_mcp.server import _escape_py_string
        assert _escape_py_string('say "hello"') == 'say \\"hello\\"'

    def test_escape_py_string_handles_newlines(self):
        from unreal_niagara_mcp.server import _escape_py_string
        assert _escape_py_string("line1\nline2") == "line1\\nline2"

    def test_format_error_returns_message_on_error(self):
        from unreal_niagara_mcp.server import _format_error
        result = _format_error({"error": True, "message": "something broke"})
        assert result == "Error: something broke"

    def test_format_error_returns_none_on_success(self):
        from unreal_niagara_mcp.server import _format_error
        result = _format_error({"data": "ok"})
        assert result is None

    def test_reset_state_clears_bridge(self):
        from unreal_niagara_mcp.server import _get_bridge, _reset_state
        bridge1 = _get_bridge()
        _reset_state()
        bridge2 = _get_bridge()
        assert bridge1 is not bridge2

    def test_get_bridge_returns_singleton(self):
        from unreal_niagara_mcp.server import _get_bridge
        b1 = _get_bridge()
        b2 = _get_bridge()
        assert b1 is b2
