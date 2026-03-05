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
# create_niagara_emitter
# ---------------------------------------------------------------------------


class TestCreateNiagaraEmitter:

    def test_creates_emitter(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_emitter

        mock_data = {"asset_path": "/Game/VFX/NE_Sparks"}
        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = create_niagara_emitter("/Game/VFX/NE_Sparks")

        assert "Created Niagara Emitter" in result
        assert "/Game/VFX/NE_Sparks" in result
        assert "CPU" in result
        assert "unsaved" in result

    def test_creates_from_template(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_emitter

        mock_data = {"asset_path": "/Game/VFX/NE_FromTemplate"}
        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = create_niagara_emitter("/Game/VFX/NE_FromTemplate", template_path="/Niagara/Templates/SimpleEmitter")

        assert "Template: /Niagara/Templates/SimpleEmitter" in result

    def test_gpu_sim_target(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_emitter

        mock_data = {"asset_path": "/Game/VFX/NE_GPU"}
        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = create_niagara_emitter("/Game/VFX/NE_GPU", sim_target="gpu")

        assert "GPU" in result

    def test_invalid_sim_target(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_emitter

        result = create_niagara_emitter("/Game/VFX/NE_Bad", sim_target="invalid")
        assert "Error" in result

    def test_handles_error(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_emitter

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(
            {"error": True, "message": "Failed to create"}
        )

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = create_niagara_emitter("/Game/VFX/NE_Fail")

        assert "Error" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_emitter
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", side_effect=EditorNotRunning("No editor")):
            result = create_niagara_emitter("/Game/VFX/NE_New")

        assert "Editor not available" in result


# ---------------------------------------------------------------------------
# create_niagara_module
# ---------------------------------------------------------------------------


class TestCreateNiagaraModule:

    def test_creates_module_with_hlsl(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_module

        mock_data = {"asset_path": "/Game/VFX/Modules/MyModule"}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = create_niagara_module(
                "/Game/VFX/Modules/MyModule",
                inputs='[{"name":"Speed","type":"float","default":"1.0"}]',
                outputs='[{"name":"Force","type":"float3"}]',
                hlsl_code="float3 Force = float3(0,0,Speed);",
            )

        assert "Created Niagara Module" in result
        assert "/Game/VFX/Modules/MyModule" in result
        assert "Inputs: 1" in result
        assert "Outputs: 1" in result
        assert "unsaved" in result

    def test_creates_module_auto_generated(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_module

        mock_data = {"asset_path": "/Game/VFX/Modules/AutoModule"}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = create_niagara_module(
                "/Game/VFX/Modules/AutoModule",
                description="Gravity force",
            )

        assert "Created Niagara Module" in result

    def test_invalid_inputs_json(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_module

        result = create_niagara_module("/Game/VFX/Modules/Bad", inputs="not json")
        assert "Error" in result

    def test_invalid_outputs_json(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_module

        result = create_niagara_module("/Game/VFX/Modules/Bad", outputs="not json")
        assert "Error" in result

    def test_handles_error(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_module

        mock_data = {"error": True, "message": "HLSL compilation failed"}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = create_niagara_module("/Game/VFX/Modules/Bad", hlsl_code="invalid;")

        assert "Error" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_module
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = create_niagara_module("/Game/VFX/Modules/M", hlsl_code="x;")

        assert "Editor not available" in result


# ---------------------------------------------------------------------------
# create_niagara_function
# ---------------------------------------------------------------------------


class TestCreateNiagaraFunction:

    def test_creates_function(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_function

        mock_data = {"asset_path": "/Game/VFX/Functions/MyFunc"}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = create_niagara_function(
                "/Game/VFX/Functions/MyFunc",
                inputs='[{"name":"Value","type":"float"}]',
                outputs='[{"name":"Result","type":"float"}]',
                hlsl_code="float Result = Value * 2.0;",
            )

        assert "Created Niagara Function" in result
        assert "/Game/VFX/Functions/MyFunc" in result
        assert "Inputs: 1" in result
        assert "Outputs: 1" in result
        assert "unsaved" in result

    def test_invalid_inputs_json(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_function

        result = create_niagara_function(
            "/Game/VFX/Functions/Bad",
            inputs="not json",
            outputs='[{"name":"R","type":"float"}]',
            hlsl_code="x;",
        )
        assert "Error" in result

    def test_invalid_outputs_json(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_function

        result = create_niagara_function(
            "/Game/VFX/Functions/Bad",
            inputs='[{"name":"V","type":"float"}]',
            outputs="not json",
            hlsl_code="x;",
        )
        assert "Error" in result

    def test_handles_error(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_function

        mock_data = {"error": True, "message": "Failed"}

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", return_value=mock_data):
            result = create_niagara_function(
                "/Game/VFX/Functions/Bad",
                inputs='[{"name":"V","type":"float"}]',
                outputs='[{"name":"R","type":"float"}]',
                hlsl_code="bad;",
            )

        assert "Error" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.creation.creation_tools import create_niagara_function
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.creation.creation_tools._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = create_niagara_function(
                "/Game/VFX/Functions/F",
                inputs='[{"name":"V","type":"float"}]',
                outputs='[{"name":"R","type":"float"}]',
                hlsl_code="float R = V;",
            )

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
