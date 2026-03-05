"""Tests for Niagara editing tools."""

import json
from unittest.mock import MagicMock, patch

import pytest

from unreal_niagara_mcp.server import _reset_state


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


def _make_plugin_success(**extra) -> dict:
    """Create a successful _call_plugin return value."""
    return {"status": "OK", **extra}


def _make_plugin_error(message: str) -> dict:
    """Create an error _call_plugin return value."""
    return {"error": True, "message": message}


# ---------------------------------------------------------------------------
# Parameter Editing
# ---------------------------------------------------------------------------


class TestTraceParameterBindings:

    def test_returns_formatted_trace(self):
        from unreal_niagara_mcp.editing.parameter_editing import trace_parameter_bindings

        mock_data = {
            "readers": [
                {"emitter": "Flames", "stage": "ParticleUpdate", "module": "Gravity Force"},
            ],
            "writers": [
                {"emitter": "Flames", "stage": "ParticleSpawn", "module": "Initialize Particle"},
            ],
        }

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", return_value=mock_data):
            result = trace_parameter_bindings("/Game/VFX/NS_Fire", "Particles.Velocity")

        assert "Parameter Trace: Particles.Velocity" in result
        assert "Writers (1)" in result
        assert "Readers (1)" in result
        assert "Initialize Particle" in result
        assert "Gravity Force" in result

    def test_handles_no_references(self):
        from unreal_niagara_mcp.editing.parameter_editing import trace_parameter_bindings

        mock_data = {"readers": [], "writers": []}

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", return_value=mock_data):
            result = trace_parameter_bindings("/Game/VFX/NS_Fire", "User.Unused")

        assert "No references found" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.editing.parameter_editing import trace_parameter_bindings
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = trace_parameter_bindings("/Game/VFX/NS_Fire", "Particles.Velocity")

        assert "Editor not available" in result

    def test_handles_plugin_error(self):
        from unreal_niagara_mcp.editing.parameter_editing import trace_parameter_bindings

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", return_value=_make_plugin_error("Not found")):
            result = trace_parameter_bindings("/Game/VFX/NS_Fire", "Bad.Param")

        assert "Error" in result
        assert "Not found" in result


class TestSetUserParameterDefault:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.parameter_editing import set_user_parameter_default

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", return_value=mock_data):
            result = set_user_parameter_default("/Game/VFX/NS_Fire", "User.SpawnRate", "200.0")

        assert "Set parameter default" in result
        assert "User.SpawnRate" in result
        assert "200.0" in result

    def test_handles_error(self):
        from unreal_niagara_mcp.editing.parameter_editing import set_user_parameter_default

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", return_value=_make_plugin_error("Type mismatch")):
            result = set_user_parameter_default("/Game/VFX/NS_Fire", "User.SpawnRate", "bad")

        assert "Error" in result


class TestAddUserParameter:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.parameter_editing import add_user_parameter

        mock_data = _make_plugin_success(name="User.NewParam")

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", return_value=mock_data):
            result = add_user_parameter("/Game/VFX/NS_Fire", "NewParam", "Float", "42.0")

        assert "Added user parameter" in result
        assert "User.NewParam" in result
        assert "Float" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.editing.parameter_editing import add_user_parameter
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = add_user_parameter("/Game/VFX/NS_Fire", "NewParam", "Float")

        assert "Editor not available" in result


class TestRemoveUserParameter:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.parameter_editing import remove_user_parameter

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", return_value=mock_data):
            result = remove_user_parameter("/Game/VFX/NS_Fire", "User.OldParam")

        assert "Removed user parameter" in result
        assert "User.OldParam" in result


class TestSetModuleInput:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.parameter_editing import set_module_input

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", return_value=mock_data):
            result = set_module_input("/Game/VFX/NS_Fire", "Flames", "Gravity Force", "Gravity Strength", "500.0")

        assert "Set module input" in result
        assert "Gravity Strength" in result
        assert "500.0" in result

    def test_handles_error(self):
        from unreal_niagara_mcp.editing.parameter_editing import set_module_input

        with patch("unreal_niagara_mcp.editing.parameter_editing._call_plugin", return_value=_make_plugin_error("Module not found")):
            result = set_module_input("/Game/VFX/NS_Fire", "Flames", "Missing", "Input", "0")

        assert "Error" in result
        assert "Module not found" in result


# ---------------------------------------------------------------------------
# Module Editing
# ---------------------------------------------------------------------------


class TestAddModule:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.module_editing import add_module

        mock_data = _make_plugin_success(index=2, guid="new-guid-123")

        with patch("unreal_niagara_mcp.editing.module_editing._call_plugin", return_value=mock_data):
            result = add_module("/Game/VFX/NS_Fire", "Flames", "ParticleUpdate", "/Niagara/Modules/Drag")

        assert "Added module" in result
        assert "ParticleUpdate" in result
        assert "new-guid-123" in result

    def test_handles_error(self):
        from unreal_niagara_mcp.editing.module_editing import add_module

        with patch("unreal_niagara_mcp.editing.module_editing._call_plugin", return_value=_make_plugin_error("Invalid script")):
            result = add_module("/Game/VFX/NS_Fire", "Flames", "ParticleUpdate", "/Bad/Path")

        assert "Error" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.editing.module_editing import add_module
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.editing.module_editing._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = add_module("/Game/VFX/NS_Fire", "Flames", "ParticleUpdate", "/Niagara/Modules/Drag")

        assert "Editor not available" in result


class TestRemoveModule:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.module_editing import remove_module

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.module_editing._call_plugin", return_value=mock_data):
            result = remove_module("/Game/VFX/NS_Fire", "Flames", "abc-123")

        assert "Removed module" in result
        assert "abc-123" in result


class TestReorderModules:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.module_editing import reorder_modules

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.module_editing._call_plugin", return_value=mock_data):
            result = reorder_modules("/Game/VFX/NS_Fire", "Flames", "ParticleUpdate", ["guid-b", "guid-a"])

        assert "Reordered modules" in result
        assert "2 module(s)" in result


class TestSetModuleEnabled:

    def test_enable_module(self):
        from unreal_niagara_mcp.editing.module_editing import set_module_enabled

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.module_editing._call_plugin", return_value=mock_data):
            result = set_module_enabled("/Game/VFX/NS_Fire", "Flames", "abc-123", True)

        assert "Module enabled" in result

    def test_disable_module(self):
        from unreal_niagara_mcp.editing.module_editing import set_module_enabled

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.module_editing._call_plugin", return_value=mock_data):
            result = set_module_enabled("/Game/VFX/NS_Fire", "Flames", "abc-123", False)

        assert "Module disabled" in result


# ---------------------------------------------------------------------------
# Emitter Editing
# ---------------------------------------------------------------------------


class TestAddEmitter:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.emitter_editing import add_emitter

        mock_data = _make_plugin_success(name="NewEmitter", handle_id="handle-abc")

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", return_value=mock_data):
            result = add_emitter("/Game/VFX/NS_Fire", "/Niagara/DefaultEmitter", "NewEmitter")

        assert "Added emitter" in result
        assert "NewEmitter" in result
        assert "handle-abc" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.editing.emitter_editing import add_emitter
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = add_emitter("/Game/VFX/NS_Fire", "/Niagara/DefaultEmitter")

        assert "Editor not available" in result


class TestRemoveEmitter:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.emitter_editing import remove_emitter

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", return_value=mock_data):
            result = remove_emitter("/Game/VFX/NS_Fire", "OldEmitter")

        assert "Removed emitter" in result
        assert "OldEmitter" in result


class TestSetEmitterEnabled:

    def test_enable_emitter(self):
        from unreal_niagara_mcp.editing.emitter_editing import set_emitter_enabled

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", return_value=mock_data):
            result = set_emitter_enabled("/Game/VFX/NS_Fire", "Flames", True)

        assert "Emitter enabled" in result

    def test_disable_emitter(self):
        from unreal_niagara_mcp.editing.emitter_editing import set_emitter_enabled

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", return_value=mock_data):
            result = set_emitter_enabled("/Game/VFX/NS_Fire", "Flames", False)

        assert "Emitter disabled" in result


class TestReorderEmitters:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.emitter_editing import reorder_emitters

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", return_value=mock_data):
            result = reorder_emitters("/Game/VFX/NS_Fire", ["Smoke", "Flames", "Sparks"])

        assert "Reordered emitters" in result
        assert "Smoke, Flames, Sparks" in result


class TestSetEmitterProperty:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.emitter_editing import set_emitter_property

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", return_value=mock_data):
            result = set_emitter_property("/Game/VFX/NS_Fire", "Flames", "sim_target", "GPUComputeSim")

        assert "Set emitter property" in result
        assert "sim_target" in result
        assert "GPUComputeSim" in result


class TestAddRenderer:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.emitter_editing import add_renderer

        mock_data = _make_plugin_success(index=1)

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", return_value=mock_data):
            result = add_renderer("/Game/VFX/NS_Fire", "Flames", "NiagaraMeshRendererProperties")

        assert "Added renderer" in result
        assert "NiagaraMeshRendererProperties" in result
        assert "Index: 1" in result


class TestRemoveRenderer:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.emitter_editing import remove_renderer

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", return_value=mock_data):
            result = remove_renderer("/Game/VFX/NS_Fire", "Flames", 0)

        assert "Removed renderer" in result
        assert "Index: 0" in result


class TestSetRendererMaterial:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.emitter_editing import set_renderer_material

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", return_value=mock_data):
            result = set_renderer_material("/Game/VFX/NS_Fire", "Flames", 0, "/Game/Materials/M_Fire")

        assert "Set renderer material" in result
        assert "M_Fire" in result


class TestSetRendererProperty:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.emitter_editing import set_renderer_property

        mock_data = _make_plugin_success()

        with patch("unreal_niagara_mcp.editing.emitter_editing._call_plugin", return_value=mock_data):
            result = set_renderer_property("/Game/VFX/NS_Fire", "Flames", 0, "sort_order_hint", "5")

        assert "Set renderer property" in result
        assert "sort_order_hint" in result
        assert "Value: 5" in result


# ---------------------------------------------------------------------------
# System Editing
# ---------------------------------------------------------------------------


class TestSetSystemProperty:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.system_editing import set_system_property

        mock_data = {"status": "OK", "property": "warmup_time", "value": "2.0"}

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.editing.system_editing._get_bridge", return_value=mock_bridge):
            result = set_system_property("/Game/VFX/NS_Fire", "warmup_time", "2.0")

        assert "Set system property" in result
        assert "warmup_time" in result
        assert "2.0" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.editing.system_editing import set_system_property
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.editing.system_editing._get_bridge", return_value=mock_bridge):
            result = set_system_property("/Game/VFX/NS_Fire", "warmup_time", "2.0")

        assert "Editor not available" in result

    def test_handles_command_failure(self):
        from unreal_niagara_mcp.editing.system_editing import set_system_property

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = {"success": False, "result": "Python error"}

        with patch("unreal_niagara_mcp.editing.system_editing._get_bridge", return_value=mock_bridge):
            result = set_system_property("/Game/VFX/NS_Fire", "warmup_time", "2.0")

        assert "Error" in result


class TestSetScalability:

    def test_returns_confirmation(self):
        from unreal_niagara_mcp.editing.system_editing import set_scalability

        mock_data = {"status": "OK", "changed": ["warmup_time", "determinism"]}

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.editing.system_editing._get_bridge", return_value=mock_bridge):
            result = set_scalability("/Game/VFX/NS_Fire", warmup_time="2.0", determinism="true")

        assert "Set scalability" in result
        assert "warmup_time" in result
        assert "determinism" in result

    def test_handles_no_properties(self):
        from unreal_niagara_mcp.editing.system_editing import set_scalability

        result = set_scalability("/Game/VFX/NS_Fire")

        assert "No properties specified" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.editing.system_editing import set_scalability
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.editing.system_editing._get_bridge", return_value=mock_bridge):
            result = set_scalability("/Game/VFX/NS_Fire", warmup_time="1.0")

        assert "Editor not available" in result


# ---------------------------------------------------------------------------
# Batch Editing
# ---------------------------------------------------------------------------


class TestBatchEditNiagara:

    def test_returns_formatted_results(self):
        from unreal_niagara_mcp.editing.batch import batch_edit_niagara

        mock_data = {
            "results": [
                {"op": "add_module", "success": True},
                {"op": "set_input", "success": True},
                {"op": "set_enabled", "success": False, "message": "Module not found"},
            ],
        }

        with patch("unreal_niagara_mcp.editing.batch._call_plugin", return_value=mock_data):
            result = batch_edit_niagara(
                "/Game/VFX/NS_Fire",
                [
                    {"op": "add_module", "emitter": "Flames", "stage": "ParticleUpdate", "module_path": "/Niagara/Drag"},
                    {"op": "set_input", "emitter": "Flames", "module": "Drag", "input": "Drag", "value": "0.5"},
                    {"op": "set_enabled", "emitter": "Flames", "module_guid": "bad", "enabled": False},
                ],
            )

        assert "3 total" in result
        assert "2 succeeded" in result
        assert "1 failed" in result
        assert "add_module: OK" in result
        assert "set_enabled: FAILED" in result
        assert "Module not found" in result

    def test_handles_rollback(self):
        from unreal_niagara_mcp.editing.batch import batch_edit_niagara

        mock_data = {
            "results": [
                {"op": "add_module", "success": False, "message": "Invalid"},
            ],
            "rolled_back": True,
        }

        with patch("unreal_niagara_mcp.editing.batch._call_plugin", return_value=mock_data):
            result = batch_edit_niagara("/Game/VFX/NS_Fire", [{"op": "add_module"}])

        assert "ROLLED BACK" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.editing.batch import batch_edit_niagara
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.editing.batch._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = batch_edit_niagara("/Game/VFX/NS_Fire", [])

        assert "Editor not available" in result

    def test_handles_plugin_error(self):
        from unreal_niagara_mcp.editing.batch import batch_edit_niagara

        with patch("unreal_niagara_mcp.editing.batch._call_plugin", return_value=_make_plugin_error("System not found")):
            result = batch_edit_niagara("/Game/VFX/NS_Fire", [])

        assert "Error" in result
        assert "System not found" in result
