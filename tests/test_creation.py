"""Tests for Niagara creation tools."""

import json
from unittest.mock import MagicMock, patch

import pytest

from unreal_niagara_mcp.server import _reset_state


@pytest.fixture(autouse=True)
def reset():
    _reset_state()
    yield
    _reset_state()


def _make_bridge_result(data) -> dict:
    return {
        "success": True,
        "output": json.dumps(data),
    }


def _make_plugin_result(data) -> dict:
    """Simulate _call_plugin return (already parsed JSON dict)."""
    return data


# ---------------------------------------------------------------------------
# create_niagara_system
# ---------------------------------------------------------------------------


class TestCreateNiagaraSystem:

    def test_creates_system(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_system

        mock_data = {"asset_path": "/Game/VFX/NS_New"}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = create_niagara_system("/Game/VFX/NS_New")

        assert "Created Niagara System" in result
        assert "/Game/VFX/NS_New" in result
        assert "unsaved" in result

    def test_creates_from_template(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_system

        mock_data = {"asset_path": "/Game/VFX/NS_FromTemplate"}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = create_niagara_system("/Game/VFX/NS_FromTemplate", template_path="/Niagara/Templates/Simple")

        assert "Template: /Niagara/Templates/Simple" in result

    def test_handles_error(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_system

        mock_data = {"error": True, "message": "Path already exists"}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = create_niagara_system("/Game/VFX/NS_Existing")

        assert "Error" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_system
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = create_niagara_system("/Game/VFX/NS_New")

        assert "Editor not available" in result


# ---------------------------------------------------------------------------
# duplicate_niagara_system
# ---------------------------------------------------------------------------


class TestDuplicateNiagaraSystem:

    def test_duplicates_successfully(self):
        from unreal_niagara_mcp.creation.creation_tools import duplicate_niagara_system

        mock_data = {"success": True, "source": "/Game/VFX/NS_A", "destination": "/Game/VFX/NS_A_Copy"}

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = duplicate_niagara_system("/Game/VFX/NS_A", "/Game/VFX/NS_A_Copy")

        assert "Duplicated" in result
        assert "NS_A" in result
        assert "NS_A_Copy" in result

    def test_handles_failure(self):
        from unreal_niagara_mcp.creation.creation_tools import duplicate_niagara_system

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(
            {"error": True, "message": "Source not found"}
        )

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = duplicate_niagara_system("/Game/VFX/Missing", "/Game/VFX/Copy")

        assert "Error" in result


# ---------------------------------------------------------------------------
# duplicate_emitter
# ---------------------------------------------------------------------------


class TestDuplicateEmitter:

    def test_duplicates_emitter(self):
        from unreal_niagara_mcp.creation.creation_tools import duplicate_emitter

        mock_data = {"new_name": "Flames_Copy"}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = duplicate_emitter("/Game/VFX/NS_Fire", "Flames", "Flames_Copy")

        assert "Duplicated Emitter" in result
        assert "Flames_Copy" in result
        assert "unsaved" in result


# ---------------------------------------------------------------------------
# clone_emitter_between_systems
# ---------------------------------------------------------------------------


class TestCloneEmitterBetweenSystems:

    def test_clones_emitter(self):
        from unreal_niagara_mcp.creation.creation_tools import clone_emitter_between_systems

        mock_data = {"emitter_name": "Sparks"}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = clone_emitter_between_systems(
                "/Game/VFX/NS_A", "Sparks", "/Game/VFX/NS_B"
            )

        assert "Cloned Emitter" in result
        assert "NS_A" in result
        assert "NS_B" in result
        assert "Sparks" in result


# ---------------------------------------------------------------------------
# create_from_preset
# ---------------------------------------------------------------------------


class TestCreateFromPreset:

    def test_creates_burst_sprite(self):
        from unreal_niagara_mcp.creation.creation_tools import create_from_preset

        mock_data = {"success": True}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = create_from_preset("/Game/VFX/NS_Burst", "burst_sprite")

        assert "burst_sprite" in result
        assert "Burst" in result
        assert "unsaved" in result

    def test_unknown_preset(self):
        from unreal_niagara_mcp.creation.creation_tools import create_from_preset

        result = create_from_preset("/Game/VFX/NS_Test", "nonexistent_preset")
        assert "Unknown preset" in result
        assert "burst_sprite" in result  # Should list available presets

    def test_all_presets_valid(self):
        """All presets should produce batch ops."""
        from unreal_niagara_mcp.creation.preset_tools import PRESETS, preset_to_batch_ops

        for name, preset in PRESETS.items():
            ops = preset_to_batch_ops(preset, f"/Game/VFX/NS_{name}")
            assert len(ops) > 0, f"Preset '{name}' produced no operations"
            assert ops[0]["op"] == "create_system"

    def test_preset_batch_ops_structure(self):
        from unreal_niagara_mcp.creation.preset_tools import PRESETS, preset_to_batch_ops

        ops = preset_to_batch_ops(PRESETS["burst_sprite"], "/Game/VFX/NS_Burst")

        # Should have: create_system, add_emitter, add_module(s), set_input(s), add_renderer
        op_types = [o["op"] for o in ops]
        assert "create_system" in op_types
        assert "add_emitter" in op_types
        assert "add_module" in op_types
        assert "add_renderer" in op_types

    def test_impact_radial_has_two_emitters(self):
        from unreal_niagara_mcp.creation.preset_tools import PRESETS, preset_to_batch_ops

        ops = preset_to_batch_ops(PRESETS["impact_radial"], "/Game/VFX/NS_Impact")
        emitter_ops = [o for o in ops if o["op"] == "add_emitter"]
        assert len(emitter_ops) == 2
        names = {o["emitter_name"] for o in emitter_ops}
        assert "Debris" in names
        assert "Dust" in names
