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


# ---------------------------------------------------------------------------
# get_niagara_renderers
# ---------------------------------------------------------------------------


class TestGetNiagaraRenderers:

    def test_returns_formatted_renderer_list(self):
        from unreal_niagara_mcp.inspection.renderer_tools import get_niagara_renderers

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [
                {
                    "name": "Flames",
                    "renderers": [
                        {
                            "index": 0,
                            "class": "NiagaraSpriteRendererProperties",
                            "is_enabled": True,
                            "sort_order_hint": 0,
                            "material": "/Game/Materials/M_Fire",
                            "bindings": [
                                {"name": "position_binding", "bound_to": "Particles.Position"},
                                {"name": "color_binding", "bound_to": "Particles.Color"},
                            ],
                        },
                    ],
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.renderer_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_renderers("/Game/VFX/NS_Fire")

        assert "NiagaraSpriteRendererProperties" in result
        assert "Enabled" in result
        assert "Sort Order: 0" in result
        assert "M_Fire" in result
        assert "position_binding -> Particles.Position" in result
        assert "color_binding -> Particles.Color" in result

    def test_handles_emitter_filter(self):
        from unreal_niagara_mcp.inspection.renderer_tools import get_niagara_renderers

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [
                {"name": "Sparks", "renderers": [{"index": 0, "class": "NiagaraSpriteRendererProperties", "is_enabled": True}]},
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.renderer_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_renderers("/Game/VFX/NS_Fire", emitter_name="Sparks")

        assert "Sparks" in result

    def test_handles_no_renderers(self):
        from unreal_niagara_mcp.inspection.renderer_tools import get_niagara_renderers

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [{"name": "Empty", "renderers": []}],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.renderer_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_renderers("/Game/VFX/NS_Fire")

        assert "no renderers" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.inspection.renderer_tools import get_niagara_renderers
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.inspection.renderer_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_renderers("/Game/VFX/NS_Fire")

        assert "Editor not available" in result


# ---------------------------------------------------------------------------
# get_niagara_modules
# ---------------------------------------------------------------------------


class TestGetNiagaraModules:

    def test_returns_formatted_module_tree(self):
        from unreal_niagara_mcp.inspection.module_tools import get_niagara_modules

        mock_data = {
            "emitters": [
                {
                    "name": "Flames",
                    "stages": {
                        "ParticleSpawn": [
                            {"index": 0, "name": "Initialize Particle", "is_enabled": True, "guid": "abc-123"},
                        ],
                        "ParticleUpdate": [
                            {"index": 0, "name": "Gravity Force", "is_enabled": True, "guid": "def-456"},
                            {"index": 1, "name": "Drag", "is_enabled": False, "guid": "ghi-789"},
                        ],
                    },
                },
            ],
        }

        mock_bridge = MagicMock()
        with patch("unreal_niagara_mcp.inspection.module_tools._call_plugin", return_value=mock_data):
            result = get_niagara_modules("/Game/VFX/NS_Fire")

        assert "Flames" in result
        assert "ParticleSpawn" in result
        assert "Initialize Particle" in result
        assert "Gravity Force" in result
        assert "[DISABLED]" in result
        assert "abc-123" in result

    def test_handles_no_modules(self):
        from unreal_niagara_mcp.inspection.module_tools import get_niagara_modules

        mock_data = {"emitters": []}

        with patch("unreal_niagara_mcp.inspection.module_tools._call_plugin", return_value=mock_data):
            result = get_niagara_modules("/Game/VFX/NS_Fire")

        assert "No modules found" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.inspection.module_tools import get_niagara_modules
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.inspection.module_tools._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = get_niagara_modules("/Game/VFX/NS_Fire")

        assert "Editor not available" in result


# ---------------------------------------------------------------------------
# get_module_inputs
# ---------------------------------------------------------------------------


class TestGetModuleInputs:

    def test_returns_formatted_input_table(self):
        from unreal_niagara_mcp.inspection.module_tools import get_module_inputs

        mock_data = {
            "inputs": [
                {"name": "Gravity Strength", "type": "Float", "value": "980.0", "default": "980.0"},
                {"name": "Apply Drag", "type": "Bool", "value": "True", "default": "False"},
            ],
        }

        with patch("unreal_niagara_mcp.inspection.module_tools._call_plugin", return_value=mock_data):
            result = get_module_inputs("/Game/VFX/NS_Fire", "Flames", "Gravity Force")

        assert "Gravity Strength" in result
        assert "Float" in result
        assert "980.0" in result
        assert "Apply Drag" in result

    def test_handles_no_inputs(self):
        from unreal_niagara_mcp.inspection.module_tools import get_module_inputs

        mock_data = {"inputs": []}

        with patch("unreal_niagara_mcp.inspection.module_tools._call_plugin", return_value=mock_data):
            result = get_module_inputs("/Game/VFX/NS_Fire", "Flames", "Empty Module")

        assert "No inputs found" in result


# ---------------------------------------------------------------------------
# get_niagara_parameters
# ---------------------------------------------------------------------------


class TestGetNiagaraParameters:

    def test_returns_grouped_parameters(self):
        from unreal_niagara_mcp.inspection.parameter_tools import get_niagara_parameters

        mock_data = {
            "namespaces": {
                "Particles": [
                    {"name": "Particles.Position", "type": "Vector", "value": "(0,0,0)"},
                    {"name": "Particles.Velocity", "type": "Vector", "value": ""},
                ],
                "User": [
                    {"name": "User.SpawnRate", "type": "Float", "value": "100.0"},
                ],
            },
        }

        with patch("unreal_niagara_mcp.inspection.parameter_tools._call_plugin", return_value=mock_data):
            result = get_niagara_parameters("/Game/VFX/NS_Fire")

        assert "Particles (2 parameter(s))" in result
        assert "User (1 parameter(s))" in result
        assert "Particles.Position (Vector) = (0,0,0)" in result
        assert "User.SpawnRate (Float) = 100.0" in result

    def test_handles_no_parameters(self):
        from unreal_niagara_mcp.inspection.parameter_tools import get_niagara_parameters

        mock_data = {"namespaces": {}}

        with patch("unreal_niagara_mcp.inspection.parameter_tools._call_plugin", return_value=mock_data):
            result = get_niagara_parameters("/Game/VFX/NS_Fire")

        assert "No parameters found" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.inspection.parameter_tools import get_niagara_parameters
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.inspection.parameter_tools._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = get_niagara_parameters("/Game/VFX/NS_Fire")

        assert "Editor not available" in result


# ---------------------------------------------------------------------------
# get_niagara_user_parameters
# ---------------------------------------------------------------------------


class TestGetNiagaraUserParameters:

    def test_returns_formatted_user_params(self):
        from unreal_niagara_mcp.inspection.parameter_tools import get_niagara_user_parameters

        mock_data = {
            "parameters": [
                {"name": "User.SpawnRate", "type": "Float", "default": "100.0"},
                {"name": "User.Color", "type": "LinearColor", "default": "(1,0,0,1)"},
            ],
        }

        with patch("unreal_niagara_mcp.inspection.parameter_tools._call_plugin", return_value=mock_data):
            result = get_niagara_user_parameters("/Game/VFX/NS_Fire")

        assert "User.SpawnRate" in result
        assert "Float" in result
        assert "100.0" in result
        assert "LinearColor" in result

    def test_handles_no_user_params(self):
        from unreal_niagara_mcp.inspection.parameter_tools import get_niagara_user_parameters

        mock_data = {"parameters": []}

        with patch("unreal_niagara_mcp.inspection.parameter_tools._call_plugin", return_value=mock_data):
            result = get_niagara_user_parameters("/Game/VFX/NS_Fire")

        assert "No user parameters found" in result


# ---------------------------------------------------------------------------
# get_data_interfaces
# ---------------------------------------------------------------------------


class TestGetDataInterfaces:

    def test_returns_formatted_di_list(self):
        from unreal_niagara_mcp.inspection.data_interface_tools import get_data_interfaces

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [
                {
                    "name": "Flames",
                    "data_interfaces": [
                        {"class": "NiagaraDataInterfaceCurve", "name": "SpawnRateCurve", "stage": "emitter_update"},
                        {"class": "NiagaraDataInterfaceSkeletalMesh", "name": "", "stage": "particle_spawn"},
                    ],
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.data_interface_tools._get_bridge", return_value=mock_bridge):
            result = get_data_interfaces("/Game/VFX/NS_Fire")

        assert "NiagaraDataInterfaceCurve" in result
        assert "SpawnRateCurve" in result
        assert "NiagaraDataInterfaceSkeletalMesh" in result
        assert "Total: 2 data interface(s)" in result

    def test_handles_no_data_interfaces(self):
        from unreal_niagara_mcp.inspection.data_interface_tools import get_data_interfaces

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [{"name": "Empty", "data_interfaces": []}],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.data_interface_tools._get_bridge", return_value=mock_bridge):
            result = get_data_interfaces("/Game/VFX/NS_Fire")

        assert "Total: 0 data interface(s)" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.inspection.data_interface_tools import get_data_interfaces
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.inspection.data_interface_tools._get_bridge", return_value=mock_bridge):
            result = get_data_interfaces("/Game/VFX/NS_Fire")

        assert "Editor not available" in result


# ---------------------------------------------------------------------------
# get_niagara_events
# ---------------------------------------------------------------------------


class TestGetNiagaraEvents:

    def test_returns_formatted_event_list(self):
        from unreal_niagara_mcp.inspection.event_tools import get_niagara_events

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [
                {
                    "name": "Sparks",
                    "events": [
                        {
                            "index": 0,
                            "source_event_name": "CollisionEvent",
                            "script_name": "ReceiveCollisionEvent",
                            "execution_mode": "SpawnedParticles",
                            "spawn_number": 5,
                            "max_events_per_frame": 0,
                        },
                    ],
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.event_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_events("/Game/VFX/NS_Fire")

        assert "CollisionEvent" in result
        assert "SpawnedParticles" in result
        assert "Spawn Number: 5" in result

    def test_handles_no_events(self):
        from unreal_niagara_mcp.inspection.event_tools import get_niagara_events

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [{"name": "Flames", "events": []}],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.event_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_events("/Game/VFX/NS_Fire")

        assert "No event handlers found" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.inspection.event_tools import get_niagara_events
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.inspection.event_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_events("/Game/VFX/NS_Fire")

        assert "Editor not available" in result


# ---------------------------------------------------------------------------
# get_simulation_stages
# ---------------------------------------------------------------------------


class TestGetSimulationStages:

    def test_returns_formatted_sim_stages(self):
        from unreal_niagara_mcp.inspection.sim_stage_tools import get_simulation_stages

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [
                {
                    "name": "Fluid",
                    "simulation_stages": [
                        {
                            "index": 0,
                            "simulation_stage_name": "PressureSolve",
                            "iteration_source": "DataInterface",
                            "num_iterations": 8,
                            "execute_before": False,
                            "enabled": True,
                            "data_interface": "NiagaraDataInterfaceGrid3D",
                        },
                    ],
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.sim_stage_tools._get_bridge", return_value=mock_bridge):
            result = get_simulation_stages("/Game/VFX/NS_Fire")

        assert "PressureSolve" in result
        assert "DataInterface" in result
        assert "Iterations: 8" in result
        assert "NiagaraDataInterfaceGrid3D" in result

    def test_handles_no_sim_stages(self):
        from unreal_niagara_mcp.inspection.sim_stage_tools import get_simulation_stages

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [{"name": "Simple", "simulation_stages": []}],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.inspection.sim_stage_tools._get_bridge", return_value=mock_bridge):
            result = get_simulation_stages("/Game/VFX/NS_Fire")

        assert "No simulation stages found" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.inspection.sim_stage_tools import get_simulation_stages
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.inspection.sim_stage_tools._get_bridge", return_value=mock_bridge):
            result = get_simulation_stages("/Game/VFX/NS_Fire")

        assert "Editor not available" in result
