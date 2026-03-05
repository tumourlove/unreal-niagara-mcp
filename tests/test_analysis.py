"""Tests for Niagara analysis tools."""

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


def _make_plugin_result(data: dict) -> dict:
    """Create a successful _call_plugin() return value (already parsed)."""
    return data


# ===========================================================================
# get_niagara_stats
# ===========================================================================


class TestGetNiagaraStats:

    def test_returns_formatted_stats(self):
        from unreal_niagara_mcp.analysis.stats_tools import get_niagara_stats

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitter_count": 3,
            "total_modules": 12,
            "total_parameters": 5,
            "renderer_types": ["NiagaraSpriteRendererProperties", "NiagaraRibbonRendererProperties"],
            "sim_targets": ["CPUSim", "GPUComputeSim"],
            "emitters": [
                {
                    "name": "Flames",
                    "is_enabled": True,
                    "sim_target": "CPUSim",
                    "modules": 4,
                    "renderers": ["NiagaraSpriteRendererProperties"],
                },
                {
                    "name": "Sparks",
                    "is_enabled": True,
                    "sim_target": "GPUComputeSim",
                    "modules": 5,
                    "renderers": ["NiagaraSpriteRendererProperties"],
                },
                {
                    "name": "Trails",
                    "is_enabled": False,
                    "sim_target": "CPUSim",
                    "modules": 3,
                    "renderers": ["NiagaraRibbonRendererProperties"],
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_stats("/Game/VFX/NS_Fire")

        assert "Niagara System Stats: /Game/VFX/NS_Fire" in result
        assert "Emitters:        3" in result
        assert "Total Modules:   12" in result
        assert "Total Parameters:" in result
        assert "NiagaraSpriteRendererProperties" in result
        assert "GPUComputeSim" in result
        assert "Flames (Enabled)" in result
        assert "Trails (Disabled)" in result

    def test_handles_empty_system(self):
        from unreal_niagara_mcp.analysis.stats_tools import get_niagara_stats

        mock_data = {
            "asset_path": "/Game/VFX/NS_Empty",
            "emitter_count": 0,
            "total_modules": 0,
            "total_parameters": 0,
            "renderer_types": [],
            "sim_targets": [],
            "emitters": [],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_stats("/Game/VFX/NS_Empty")

        assert "Emitters:        0" in result
        assert "(none)" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.analysis.stats_tools import get_niagara_stats
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_stats("/Game/VFX/NS_Fire")

        assert "Editor not available" in result

    def test_handles_asset_not_found(self):
        from unreal_niagara_mcp.analysis.stats_tools import get_niagara_stats

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(
            {"error": True, "message": "Cannot load asset: /Game/Missing"}
        )

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_stats("/Game/Missing")

        assert "Error" in result
        assert "Cannot load asset" in result


# ===========================================================================
# audit_niagara_system
# ===========================================================================


class TestAuditNiagaraSystem:

    def test_reports_errors_warnings_and_info(self):
        from unreal_niagara_mcp.analysis.stats_tools import audit_niagara_system

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "findings": [
                {
                    "severity": "ERROR",
                    "description": "Missing renderer on enabled emitter",
                    "emitter": "Sparks",
                },
                {
                    "severity": "WARNING",
                    "description": "GPU emitter without fixed bounds",
                    "emitter": "Flames",
                },
                {
                    "severity": "WARNING",
                    "description": "More than 10 modules in Particle Update (12)",
                    "emitter": "Flames",
                },
                {
                    "severity": "INFO",
                    "description": "Could benefit from scalability settings",
                    "emitter": "(system)",
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):
            result = audit_niagara_system("/Game/VFX/NS_Fire")

        assert "1 error(s), 2 warning(s), 1 info(s)" in result
        assert "[ERROR] Missing renderer" in result
        assert "Emitter: Sparks" in result
        assert "[WARNING] GPU emitter without fixed bounds" in result
        assert "[INFO] Could benefit from scalability settings" in result

    def test_no_findings(self):
        from unreal_niagara_mcp.analysis.stats_tools import audit_niagara_system

        mock_data = {
            "asset_path": "/Game/VFX/NS_Clean",
            "findings": [],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):
            result = audit_niagara_system("/Game/VFX/NS_Clean")

        assert "No issues found" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.analysis.stats_tools import audit_niagara_system
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):
            result = audit_niagara_system("/Game/VFX/NS_Fire")

        assert "Editor not available" in result

    def test_info_only_report(self):
        from unreal_niagara_mcp.analysis.stats_tools import audit_niagara_system

        mock_data = {
            "asset_path": "/Game/VFX/NS_Simple",
            "findings": [
                {
                    "severity": "INFO",
                    "description": "System has no user parameters (not configurable)",
                    "emitter": "(system)",
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):
            result = audit_niagara_system("/Game/VFX/NS_Simple")

        assert "0 error(s), 0 warning(s), 1 info(s)" in result
        assert "no user parameters" in result


# ===========================================================================
# audit_scalability
# ===========================================================================


class TestAuditScalability:

    def test_returns_scalability_report(self):
        from unreal_niagara_mcp.analysis.stats_tools import audit_scalability

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "system_settings": {
                "effect_type": None,
                "warmup_time": 0.0,
            },
            "emitters": [
                {
                    "name": "Flames",
                    "sim_target": "CPUSim",
                    "bounds_mode": "Dynamic",
                    "has_scalability_overrides": False,
                },
            ],
            "recommendations": [
                "No effect type set - consider assigning one for scalability budgets",
                "Emitter 'Flames' has no scalability overrides",
                "Emitter 'Flames' uses Dynamic bounds - consider Fixed for performance",
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):
            result = audit_scalability("/Game/VFX/NS_Fire")

        assert "Scalability Audit" in result
        assert "(not set)" in result
        assert "Dynamic" in result
        assert "Scalability Overrides: No" in result
        assert "No effect type set" in result

    def test_clean_scalability(self):
        from unreal_niagara_mcp.analysis.stats_tools import audit_scalability

        mock_data = {
            "asset_path": "/Game/VFX/NS_Good",
            "system_settings": {
                "effect_type": "Fire",
                "warmup_time": 0.5,
            },
            "emitters": [
                {
                    "name": "Flames",
                    "sim_target": "CPUSim",
                    "bounds_mode": "Fixed",
                    "has_scalability_overrides": True,
                },
            ],
            "recommendations": [],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):
            result = audit_scalability("/Game/VFX/NS_Good")

        assert "Effect Type:  Fire" in result
        assert "Scalability Overrides: Yes" in result
        assert "No scalability issues found" in result


# ===========================================================================
# audit_pooling
# ===========================================================================


class TestAuditPooling:

    def test_no_pooling_with_burst(self):
        from unreal_niagara_mcp.analysis.audit_tools import audit_pooling

        mock_data = {
            "asset_path": "/Game/VFX/NS_Impact",
            "pool_method": "None",
            "pool_prime_size": 0,
            "auto_deactivate": False,
            "uses_pooling": False,
            "emitter_count": 2,
            "has_burst_spawn": True,
            "has_continuous_spawn": False,
            "recommendations": [
                "System uses burst spawning - good candidate for pooling",
                "Recommended pool size: 4-8 instances",
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.audit_tools._get_bridge", return_value=mock_bridge):
            result = audit_pooling("/Game/VFX/NS_Impact")

        assert "Pooling Audit" in result
        assert "Uses Pooling:    No" in result
        assert "Has Burst Spawn:     Yes" in result
        assert "good candidate for pooling" in result

    def test_pooling_enabled_no_prime(self):
        from unreal_niagara_mcp.analysis.audit_tools import audit_pooling

        mock_data = {
            "asset_path": "/Game/VFX/NS_Pooled",
            "pool_method": "AutoRelease",
            "pool_prime_size": 0,
            "auto_deactivate": True,
            "uses_pooling": True,
            "emitter_count": 1,
            "has_burst_spawn": True,
            "has_continuous_spawn": False,
            "recommendations": [
                "Pooling is enabled (AutoRelease) but pool_prime_size is 0 - consider priming",
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.audit_tools._get_bridge", return_value=mock_bridge):
            result = audit_pooling("/Game/VFX/NS_Pooled")

        assert "Uses Pooling:    Yes" in result
        assert "consider priming" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.analysis.audit_tools import audit_pooling
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.analysis.audit_tools._get_bridge", return_value=mock_bridge):
            result = audit_pooling("/Game/VFX/NS_Fire")

        assert "Editor not available" in result


# ===========================================================================
# validate_bindings
# ===========================================================================


class TestValidateBindings:

    def test_reports_broken_bindings(self):
        from unreal_niagara_mcp.analysis.audit_tools import validate_bindings

        mock_data = {
            "total_checked": 5,
            "total_broken": 1,
            "total_warnings": 1,
            "emitters": [
                {
                    "name": "Flames",
                    "bindings": [
                        {"module": "SpawnRate", "input": "Rate", "status": "valid"},
                        {"module": "Gravity", "input": "GravityForce", "status": "valid"},
                        {
                            "module": "ScaleColor",
                            "input": "ColorScale",
                            "status": "broken",
                            "bound_to": "User.MyDeletedParam",
                            "suggestion": "Check if parameter was renamed",
                        },
                        {
                            "module": "SpriteSize",
                            "input": "SizeScale",
                            "status": "warning",
                            "message": "Bound to default value - may be intentional",
                        },
                        {"module": "Lifetime", "input": "MaxLifetime", "status": "valid"},
                    ],
                },
            ],
        }

        with patch("unreal_niagara_mcp.analysis.audit_tools._call_plugin", return_value=mock_data):
            result = validate_bindings("/Game/VFX/NS_Fire")

        assert "5 binding(s) checked" in result
        assert "1 broken" in result
        assert "[BROKEN] ScaleColor.ColorScale" in result
        assert "User.MyDeletedParam" in result
        assert "[WARNING] SpriteSize.SizeScale" in result

    def test_all_bindings_valid(self):
        from unreal_niagara_mcp.analysis.audit_tools import validate_bindings

        mock_data = {
            "total_checked": 3,
            "total_broken": 0,
            "total_warnings": 0,
            "emitters": [
                {
                    "name": "Flames",
                    "bindings": [
                        {"module": "SpawnRate", "input": "Rate", "status": "valid"},
                        {"module": "Gravity", "input": "GravityForce", "status": "valid"},
                        {"module": "Lifetime", "input": "MaxLifetime", "status": "valid"},
                    ],
                },
            ],
        }

        with patch("unreal_niagara_mcp.analysis.audit_tools._call_plugin", return_value=mock_data):
            result = validate_bindings("/Game/VFX/NS_Fire")

        assert "All 3 binding(s) valid" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.analysis.audit_tools import validate_bindings
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        with patch("unreal_niagara_mcp.analysis.audit_tools._call_plugin", side_effect=EditorNotRunning("No editor")):
            result = validate_bindings("/Game/VFX/NS_Fire")

        assert "Editor not available" in result

    def test_no_emitters(self):
        from unreal_niagara_mcp.analysis.audit_tools import validate_bindings

        mock_data = {
            "total_checked": 0,
            "total_broken": 0,
            "total_warnings": 0,
            "emitters": [],
        }

        with patch("unreal_niagara_mcp.analysis.audit_tools._call_plugin", return_value=mock_data):
            result = validate_bindings("/Game/VFX/NS_Empty")

        assert "No emitters to validate" in result


# ===========================================================================
# get_emitter_summary
# ===========================================================================


class TestGetEmitterSummary:

    def test_generates_natural_language_summary(self):
        from unreal_niagara_mcp.analysis.summary_tools import get_emitter_summary

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitter": {
                "name": "Flames",
                "is_enabled": True,
                "sim_target": "GPUComputeSim",
                "local_space": False,
                "bounds_mode": "Fixed",
                "modules": {
                    "particle_spawn": ["SpawnRate", "InitialVelocity"],
                    "particle_update": ["Gravity", "ScaleSize", "ColorOverLife"],
                },
                "renderers": [
                    {"class": "NiagaraSpriteRendererProperties", "material": "M_Flame", "is_enabled": True},
                ],
            },
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.summary_tools._get_bridge", return_value=mock_bridge):
            result = get_emitter_summary("/Game/VFX/NS_Fire", "Flames")

        assert "Emitter Summary: Flames" in result
        assert "GPU" in result
        assert "world space" in result
        assert "Fixed" in result
        assert "SpawnRate" in result
        assert "Gravity" in result
        assert "NiagaraSpriteRendererProperties" in result
        assert "M_Flame" in result

    def test_disabled_emitter(self):
        from unreal_niagara_mcp.analysis.summary_tools import get_emitter_summary

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitter": {
                "name": "Smoke",
                "is_enabled": False,
                "sim_target": "CPUSim",
                "local_space": True,
                "bounds_mode": "Dynamic",
                "modules": {},
                "renderers": [],
            },
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.summary_tools._get_bridge", return_value=mock_bridge):
            result = get_emitter_summary("/Game/VFX/NS_Fire", "Smoke")

        assert "currently disabled" in result
        assert "local space" in result
        assert "No renderers configured" in result

    def test_emitter_not_found(self):
        from unreal_niagara_mcp.analysis.summary_tools import get_emitter_summary

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(
            {"error": True, "message": "Emitter 'Missing' not found in /Game/VFX/NS_Fire"}
        )

        with patch("unreal_niagara_mcp.analysis.summary_tools._get_bridge", return_value=mock_bridge):
            result = get_emitter_summary("/Game/VFX/NS_Fire", "Missing")

        assert "Error" in result
        assert "not found" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.analysis.summary_tools import get_emitter_summary
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.analysis.summary_tools._get_bridge", return_value=mock_bridge):
            result = get_emitter_summary("/Game/VFX/NS_Fire", "Flames")

        assert "Editor not available" in result


# ===========================================================================
# get_module_graph
# ===========================================================================


class TestGetModuleGraph:

    def test_returns_graph_with_nodes_and_connections(self):
        from unreal_niagara_mcp.analysis.hlsl_output_tools import get_module_graph

        mock_data = {
            "module_name": "MyCustomModule",
            "script_path": "/Game/VFX/Modules/MyCustomModule",
            "nodes": [
                {
                    "id": 0,
                    "type": "InputMap",
                    "name": "Input",
                    "inputs": [],
                    "outputs": [{"name": "Value", "type": "float"}],
                },
                {
                    "id": 1,
                    "type": "Multiply",
                    "name": "Mul",
                    "inputs": [{"name": "A", "type": "float"}, {"name": "B", "type": "float"}],
                    "outputs": [{"name": "Result", "type": "float"}],
                },
            ],
            "connections": [
                {"source_node": "Input", "source_pin": "Value", "target_node": "Mul", "target_pin": "A"},
            ],
            "hlsl_expressions": [
                {"node_name": "CustomHLSL_0", "code": "float x = Input.Value;\nreturn x * x;"},
            ],
        }

        with patch("unreal_niagara_mcp.analysis.hlsl_output_tools._call_plugin", return_value=mock_data):
            result = get_module_graph("/Game/VFX/Modules/MyCustomModule")

        assert "Module Graph: MyCustomModule" in result
        assert "Nodes (2)" in result
        assert "InputMap: Input" in result
        assert "Multiply: Mul" in result
        assert "Connections (1)" in result
        assert "Input.Value -> Mul.A" in result
        assert "Custom HLSL Expressions" in result
        assert "float x = Input.Value;" in result

    def test_no_graph_data(self):
        from unreal_niagara_mcp.analysis.hlsl_output_tools import get_module_graph

        mock_data = {
            "module_name": "BuiltInModule",
            "script_path": "/Niagara/Modules/BuiltIn",
            "nodes": [],
            "connections": [],
            "hlsl_expressions": [],
        }

        with patch("unreal_niagara_mcp.analysis.hlsl_output_tools._call_plugin", return_value=mock_data):
            result = get_module_graph("/Niagara/Modules/BuiltIn")

        assert "No graph data available" in result

    def test_handles_error(self):
        from unreal_niagara_mcp.analysis.hlsl_output_tools import get_module_graph

        mock_data = {"error": True, "message": "Module not found"}

        with patch("unreal_niagara_mcp.analysis.hlsl_output_tools._call_plugin", return_value=mock_data):
            result = get_module_graph("/Game/Missing")

        assert "Error" in result
        assert "Module not found" in result


# ===========================================================================
# get_di_functions
# ===========================================================================


class TestGetDIFunctions:

    def test_returns_function_signatures(self):
        from unreal_niagara_mcp.analysis.hlsl_output_tools import get_di_functions

        mock_data = {
            "class_name": "NiagaraDataInterfaceCurve",
            "functions": [
                {
                    "name": "SampleCurve",
                    "return_type": "float",
                    "parameters": [
                        {"name": "CurveIndex", "type": "int", "direction": "in"},
                        {"name": "Time", "type": "float", "direction": "in"},
                    ],
                    "description": "Sample a curve at the given time",
                },
                {
                    "name": "GetNumCurves",
                    "return_type": "int",
                    "parameters": [],
                    "description": "Get the number of curves",
                },
            ],
        }

        with patch("unreal_niagara_mcp.analysis.hlsl_output_tools._call_plugin", return_value=mock_data):
            result = get_di_functions("NiagaraDataInterfaceCurve")

        assert "Data Interface Functions: NiagaraDataInterfaceCurve" in result
        assert "2 function(s)" in result
        assert "float SampleCurve(int CurveIndex, float Time)" in result
        assert "int GetNumCurves()" in result
        assert "Sample a curve at the given time" in result

    def test_no_functions(self):
        from unreal_niagara_mcp.analysis.hlsl_output_tools import get_di_functions

        mock_data = {
            "class_name": "NiagaraDataInterfaceEmpty",
            "functions": [],
        }

        with patch("unreal_niagara_mcp.analysis.hlsl_output_tools._call_plugin", return_value=mock_data):
            result = get_di_functions("NiagaraDataInterfaceEmpty")

        assert "No functions found" in result

    def test_out_parameters(self):
        from unreal_niagara_mcp.analysis.hlsl_output_tools import get_di_functions

        mock_data = {
            "class_name": "NiagaraDataInterfaceMesh",
            "functions": [
                {
                    "name": "GetTriPosition",
                    "return_type": "void",
                    "parameters": [
                        {"name": "TriIndex", "type": "int", "direction": "in"},
                        {"name": "BaryCoord", "type": "float3", "direction": "in"},
                        {"name": "OutPosition", "type": "float3", "direction": "out"},
                    ],
                },
            ],
        }

        with patch("unreal_niagara_mcp.analysis.hlsl_output_tools._call_plugin", return_value=mock_data):
            result = get_di_functions("NiagaraDataInterfaceMesh")

        assert "out float3 OutPosition" in result


# ===========================================================================
# preview_particle_count
# ===========================================================================


class TestPreviewParticleCount:

    def test_continuous_spawn_preview(self):
        from unreal_niagara_mcp.analysis.dream_tools import preview_particle_count

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [
                {
                    "name": "Flames",
                    "spawn_type": "continuous",
                    "spawn_rate": 100.0,
                    "burst_count": 0,
                    "lifetime": 2.0,
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.dream_tools._get_bridge", return_value=mock_bridge):
            result = preview_particle_count("/Game/VFX/NS_Fire")

        assert "Particle Count Preview" in result
        assert "Spawn Type: continuous" in result
        assert "Spawn Rate: 100.0/s" in result
        assert "Lifetime: 2.0s" in result
        assert "Peak Particles: 200" in result

    def test_burst_spawn_preview(self):
        from unreal_niagara_mcp.analysis.dream_tools import preview_particle_count

        mock_data = {
            "asset_path": "/Game/VFX/NS_Impact",
            "emitters": [
                {
                    "name": "Debris",
                    "spawn_type": "burst",
                    "spawn_rate": 0.0,
                    "burst_count": 50,
                    "lifetime": 1.0,
                },
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.dream_tools._get_bridge", return_value=mock_bridge):
            result = preview_particle_count("/Game/VFX/NS_Impact", time_range=3.0)

        assert "Burst Count: 50" in result
        assert "Peak Particles: 50" in result

    def test_no_emitters(self):
        from unreal_niagara_mcp.analysis.dream_tools import preview_particle_count

        mock_data = {
            "asset_path": "/Game/VFX/NS_Empty",
            "emitters": [],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.analysis.dream_tools._get_bridge", return_value=mock_bridge):
            result = preview_particle_count("/Game/VFX/NS_Empty")

        assert "No enabled emitters" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.analysis.dream_tools import preview_particle_count
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.analysis.dream_tools._get_bridge", return_value=mock_bridge):
            result = preview_particle_count("/Game/VFX/NS_Fire")

        assert "Editor not available" in result


# ===========================================================================
# _compute_particle_table (unit test for pure math)
# ===========================================================================


class TestComputeParticleTable:

    def test_continuous_reaches_steady_state(self):
        from unreal_niagara_mcp.analysis.dream_tools import _compute_particle_table

        table = _compute_particle_table("continuous", 100.0, 0, 2.0, 5.0)

        # At t=0, alive=0
        assert table[0]["alive"] == 0.0
        # At t=2.0 (step 4 of 10 with dt=0.5), alive should be 200
        # Find the entry at t=2.0
        at_2s = [r for r in table if abs(r["time"] - 2.0) < 0.01]
        assert len(at_2s) == 1
        assert at_2s[0]["alive"] == 200.0

        # After lifetime, should stay at 200 (steady state)
        at_5s = table[-1]
        assert at_5s["alive"] == 200.0

    def test_burst_decays(self):
        from unreal_niagara_mcp.analysis.dream_tools import _compute_particle_table

        table = _compute_particle_table("burst", 0.0, 50, 1.0, 3.0)

        # At t=0, alive=50
        assert table[0]["alive"] == 50.0
        # After lifetime (t>=1.0), alive=0
        at_3s = table[-1]
        assert at_3s["alive"] == 0.0

    def test_unknown_spawn_type(self):
        from unreal_niagara_mcp.analysis.dream_tools import _compute_particle_table

        table = _compute_particle_table("unknown", 100.0, 50, 2.0, 5.0)
        # All entries should be 0
        for row in table:
            assert row["alive"] == 0.0


# ===========================================================================
# get_hlsl_output
# ===========================================================================


class TestGetHLSLOutput:

    def test_returns_hlsl_code(self):
        from unreal_niagara_mcp.analysis.dream_tools import get_hlsl_output

        mock_data = {
            "emitter_name": "Sparks",
            "compile_status": "Success",
            "hlsl": "void SimulateMain()\n{\n  float3 Pos = Particles.Position;\n  Pos += Particles.Velocity * DeltaTime;\n  Particles.Position = Pos;\n}\n",
        }

        with patch("unreal_niagara_mcp.analysis.dream_tools._call_plugin", return_value=mock_data):
            result = get_hlsl_output("/Game/VFX/NS_Fire", "Sparks")

        assert "Compiled GPU HLSL: Sparks" in result
        assert "Compile Status: Success" in result
        assert "--- HLSL BEGIN ---" in result
        assert "SimulateMain" in result
        assert "--- HLSL END ---" in result
        assert "Total Lines:" in result

    def test_no_hlsl_available(self):
        from unreal_niagara_mcp.analysis.dream_tools import get_hlsl_output

        mock_data = {
            "emitter_name": "CPUEmitter",
            "compile_status": "N/A",
            "hlsl": "",
        }

        with patch("unreal_niagara_mcp.analysis.dream_tools._call_plugin", return_value=mock_data):
            result = get_hlsl_output("/Game/VFX/NS_Fire", "CPUEmitter")

        assert "No HLSL output available" in result

    def test_handles_error(self):
        from unreal_niagara_mcp.analysis.dream_tools import get_hlsl_output

        mock_data = {"error": True, "message": "Emitter not found"}

        with patch("unreal_niagara_mcp.analysis.dream_tools._call_plugin", return_value=mock_data):
            result = get_hlsl_output("/Game/VFX/NS_Fire", "Missing")

        assert "Error" in result


# ===========================================================================
# batch_update_niagara
# ===========================================================================


class TestBatchUpdateNiagara:

    def test_successful_batch(self):
        from unreal_niagara_mcp.analysis.dream_tools import batch_update_niagara

        call_count = 0

        def mock_plugin(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"success": True}

        updates = json.dumps([
            {
                "asset_path": "/Game/VFX/NS_Fire",
                "operations": [
                    {"op": "set_input", "emitter": "Flames", "module": "SpawnRate", "input": "SpawnRate", "value": "200"},
                    {"op": "enable_emitter", "emitter": "Smoke", "enabled": True},
                ],
            },
        ])

        with patch("unreal_niagara_mcp.analysis.dream_tools._call_plugin", side_effect=mock_plugin):
            result = batch_update_niagara(updates)

        assert "Total Operations: 2" in result
        assert "Successful: 2" in result
        assert "Failed: 0" in result
        assert call_count == 2

    def test_mixed_results(self):
        from unreal_niagara_mcp.analysis.dream_tools import batch_update_niagara

        responses = [
            {"success": True},
            {"error": True, "message": "Module not found"},
        ]
        call_idx = 0

        def mock_plugin(*args, **kwargs):
            nonlocal call_idx
            resp = responses[call_idx]
            call_idx += 1
            return resp

        updates = json.dumps([
            {
                "asset_path": "/Game/VFX/NS_Fire",
                "operations": [
                    {"op": "set_input", "emitter": "Flames", "module": "SpawnRate", "input": "Rate", "value": "100"},
                    {"op": "set_input", "emitter": "Flames", "module": "Missing", "input": "X", "value": "1"},
                ],
            },
        ])

        with patch("unreal_niagara_mcp.analysis.dream_tools._call_plugin", side_effect=mock_plugin):
            result = batch_update_niagara(updates)

        assert "Successful: 1" in result
        assert "Failed: 1" in result
        assert "[OK]" in result
        assert "[FAIL]" in result
        assert "Module not found" in result

    def test_invalid_json(self):
        from unreal_niagara_mcp.analysis.dream_tools import batch_update_niagara

        result = batch_update_niagara("not valid json{{{")
        assert "Error" in result
        assert "Invalid JSON" in result

    def test_not_array(self):
        from unreal_niagara_mcp.analysis.dream_tools import batch_update_niagara

        result = batch_update_niagara('{"not": "array"}')
        assert "Error" in result
        assert "must be a JSON array" in result

    def test_unknown_operation(self):
        from unreal_niagara_mcp.analysis.dream_tools import batch_update_niagara

        updates = json.dumps([
            {
                "asset_path": "/Game/VFX/NS_Fire",
                "operations": [
                    {"op": "delete_everything"},
                ],
            },
        ])

        with patch("unreal_niagara_mcp.analysis.dream_tools._call_plugin",
                    return_value={"error": True, "message": "Unknown operation: delete_everything"}):
            result = batch_update_niagara(updates)

        assert "Failed: 1" in result

    def test_missing_asset_path(self):
        from unreal_niagara_mcp.analysis.dream_tools import batch_update_niagara

        updates = json.dumps([
            {
                "operations": [
                    {"op": "set_input", "emitter": "E", "module": "M", "input": "I", "value": "V"},
                ],
            },
        ])

        result = batch_update_niagara(updates)
        assert "Failed: 1" in result

    def test_editor_not_running(self):
        from unreal_niagara_mcp.analysis.dream_tools import batch_update_niagara
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        updates = json.dumps([
            {
                "asset_path": "/Game/VFX/NS_Fire",
                "operations": [
                    {"op": "set_input", "emitter": "E", "module": "M", "input": "I", "value": "V"},
                ],
            },
        ])

        with patch("unreal_niagara_mcp.analysis.dream_tools._call_plugin",
                    side_effect=EditorNotRunning("No editor")):
            result = batch_update_niagara(updates)

        assert "Failed: 1" in result
        assert "Editor not available" in result
