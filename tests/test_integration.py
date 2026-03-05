"""End-to-end integration tests with mocked bridge verifying multi-tool workflows."""

import json
from unittest.mock import MagicMock, patch, call

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


# ===========================================================================
# Workflow 1: Inspect system -> audit -> get stats
# ===========================================================================


class TestInspectAndAuditWorkflow:
    """Simulates: get system info -> list emitters -> audit system -> get stats."""

    def test_full_inspection_workflow(self):
        from unreal_niagara_mcp.inspection.system_tools import (
            get_niagara_system_info,
            get_niagara_emitters,
        )
        from unreal_niagara_mcp.analysis.stats_tools import (
            audit_niagara_system,
            get_niagara_stats,
        )

        mock_bridge = MagicMock()

        # Step 1: System info
        system_info = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitter_count": 2,
            "warmup_time": 0.5,
            "warmup_tick_count": 5,
            "warmup_tick_delta": 0.033,
            "determinism": False,
            "fixed_tick_delta": False,
            "fixed_tick_delta_time": 0.0167,
        }

        # Step 2: Emitters
        emitters_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [
                {
                    "name": "Flames",
                    "is_enabled": True,
                    "sim_target": "GPUComputeSim",
                    "local_space": False,
                    "bounds_mode": "Dynamic",
                    "renderer_count": 1,
                },
                {
                    "name": "Sparks",
                    "is_enabled": True,
                    "sim_target": "CPUSim",
                    "local_space": False,
                    "bounds_mode": "Auto",
                    "renderer_count": 0,
                },
            ],
        }

        # Step 3: Audit
        audit_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "findings": [
                {
                    "severity": "WARNING",
                    "description": "GPU emitter without fixed bounds",
                    "emitter": "Flames",
                },
                {
                    "severity": "ERROR",
                    "description": "Missing renderer on enabled emitter",
                    "emitter": "Sparks",
                },
                {
                    "severity": "INFO",
                    "description": "Could benefit from scalability settings",
                    "emitter": "(system)",
                },
            ],
        }

        # Step 4: Stats
        stats_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitter_count": 2,
            "total_modules": 8,
            "total_parameters": 3,
            "renderer_types": ["NiagaraSpriteRendererProperties"],
            "sim_targets": ["GPUComputeSim", "CPUSim"],
            "emitters": [
                {"name": "Flames", "is_enabled": True, "sim_target": "GPUComputeSim", "modules": 5, "renderers": ["NiagaraSpriteRendererProperties"]},
                {"name": "Sparks", "is_enabled": True, "sim_target": "CPUSim", "modules": 3, "renderers": []},
            ],
        }

        mock_bridge.run_command.side_effect = [
            _make_bridge_result(system_info),
            _make_bridge_result(emitters_data),
            _make_bridge_result(audit_data),
            _make_bridge_result(stats_data),
        ]

        with patch("unreal_niagara_mcp.inspection.system_tools._get_bridge", return_value=mock_bridge), \
             patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge):

            # Step 1
            info_result = get_niagara_system_info("/Game/VFX/NS_Fire")
            assert "Emitter Count: 2" in info_result

            # Step 2
            emitters_result = get_niagara_emitters("/Game/VFX/NS_Fire")
            assert "Flames (Enabled)" in emitters_result
            assert "Sparks (Enabled)" in emitters_result

            # Step 3
            audit_result = audit_niagara_system("/Game/VFX/NS_Fire")
            assert "1 error(s)" in audit_result
            assert "GPU emitter without fixed bounds" in audit_result
            assert "Missing renderer" in audit_result

            # Step 4
            stats_result = get_niagara_stats("/Game/VFX/NS_Fire")
            assert "Total Modules:   8" in stats_result

        assert mock_bridge.run_command.call_count == 4


# ===========================================================================
# Workflow 2: Audit -> particle preview -> fix issues
# ===========================================================================


class TestAuditAndPreviewWorkflow:
    """Simulates: audit system -> preview particle counts -> batch fix."""

    def test_audit_preview_and_batch_fix(self):
        from unreal_niagara_mcp.analysis.stats_tools import audit_niagara_system
        from unreal_niagara_mcp.analysis.dream_tools import (
            preview_particle_count,
            batch_update_niagara,
        )

        mock_bridge = MagicMock()

        # Step 1: Audit
        audit_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "findings": [
                {
                    "severity": "WARNING",
                    "description": "GPU emitter without fixed bounds",
                    "emitter": "Flames",
                },
            ],
        }

        # Step 2: Preview
        preview_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitters": [
                {
                    "name": "Flames",
                    "spawn_type": "continuous",
                    "spawn_rate": 500.0,
                    "burst_count": 0,
                    "lifetime": 2.0,
                },
            ],
        }

        mock_bridge.run_command.side_effect = [
            _make_bridge_result(audit_data),
            _make_bridge_result(preview_data),
        ]

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge), \
             patch("unreal_niagara_mcp.analysis.dream_tools._get_bridge", return_value=mock_bridge):

            # Step 1: Audit reveals GPU emitter issues
            audit_result = audit_niagara_system("/Game/VFX/NS_Fire")
            assert "GPU emitter without fixed bounds" in audit_result

            # Step 2: Preview shows high particle count
            preview_result = preview_particle_count("/Game/VFX/NS_Fire", "Flames")
            assert "Peak Particles: 1000" in preview_result
            assert "Spawn Rate: 500.0/s" in preview_result

        # Step 3: Batch fix - reduce spawn rate
        updates = json.dumps([
            {
                "asset_path": "/Game/VFX/NS_Fire",
                "operations": [
                    {"op": "set_input", "emitter": "Flames", "module": "SpawnRate", "input": "SpawnRate", "value": "200"},
                ],
            },
        ])

        with patch("unreal_niagara_mcp.analysis.dream_tools._call_plugin", return_value={"success": True}):
            batch_result = batch_update_niagara(updates)

        assert "Successful: 1" in batch_result
        assert "Failed: 0" in batch_result


# ===========================================================================
# Workflow 3: Emitter summary + bindings validation
# ===========================================================================


class TestSummaryAndValidationWorkflow:
    """Simulates: get emitter summary -> validate bindings."""

    def test_summary_then_validate(self):
        from unreal_niagara_mcp.analysis.summary_tools import get_emitter_summary
        from unreal_niagara_mcp.analysis.audit_tools import validate_bindings

        mock_bridge = MagicMock()

        # Step 1: Emitter summary
        summary_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitter": {
                "name": "Flames",
                "is_enabled": True,
                "sim_target": "GPUComputeSim",
                "local_space": False,
                "bounds_mode": "Fixed",
                "modules": {
                    "particle_spawn": ["SpawnRate", "ConeVelocity"],
                    "particle_update": ["Gravity", "Drag", "ScaleOverLife", "ColorOverLife"],
                },
                "renderers": [
                    {"class": "NiagaraSpriteRendererProperties", "material": "M_Flame", "is_enabled": True},
                ],
            },
        }

        mock_bridge.run_command.return_value = _make_bridge_result(summary_data)

        with patch("unreal_niagara_mcp.analysis.summary_tools._get_bridge", return_value=mock_bridge):
            summary_result = get_emitter_summary("/Game/VFX/NS_Fire", "Flames")

        assert "GPU" in summary_result
        assert "world space" in summary_result
        assert "SpawnRate" in summary_result
        assert "M_Flame" in summary_result

        # Step 2: Validate bindings
        bindings_data = {
            "total_checked": 6,
            "total_broken": 0,
            "total_warnings": 0,
            "emitters": [
                {
                    "name": "Flames",
                    "bindings": [
                        {"module": "SpawnRate", "input": "Rate", "status": "valid"},
                        {"module": "ConeVelocity", "input": "Angle", "status": "valid"},
                        {"module": "Gravity", "input": "GravityForce", "status": "valid"},
                        {"module": "Drag", "input": "DragCoefficient", "status": "valid"},
                        {"module": "ScaleOverLife", "input": "Curve", "status": "valid"},
                        {"module": "ColorOverLife", "input": "ColorCurve", "status": "valid"},
                    ],
                },
            ],
        }

        with patch("unreal_niagara_mcp.analysis.audit_tools._call_plugin", return_value=bindings_data):
            bindings_result = validate_bindings("/Game/VFX/NS_Fire", "Flames")

        assert "6 binding(s) checked" in bindings_result
        assert "0 broken" in bindings_result
        assert "All 6 binding(s) valid" in bindings_result


# ===========================================================================
# Workflow 4: Module graph + DI functions inspection
# ===========================================================================


class TestModuleGraphWorkflow:
    """Simulates: get module graph -> get DI functions."""

    def test_inspect_module_then_di(self):
        from unreal_niagara_mcp.analysis.hlsl_output_tools import (
            get_module_graph,
            get_di_functions,
        )

        # Step 1: Module graph shows it uses a curve DI
        graph_data = {
            "module_name": "ScaleOverLife",
            "script_path": "/Niagara/Modules/ScaleOverLife",
            "nodes": [
                {"id": 0, "type": "Input", "name": "CurveInput", "inputs": [], "outputs": [{"name": "Curve", "type": "DataInterface"}]},
                {"id": 1, "type": "SampleCurve", "name": "Sample", "inputs": [{"name": "Curve", "type": "DataInterface"}, {"name": "T", "type": "float"}], "outputs": [{"name": "Value", "type": "float"}]},
                {"id": 2, "type": "Multiply", "name": "ApplyScale", "inputs": [{"name": "A", "type": "float3"}, {"name": "B", "type": "float"}], "outputs": [{"name": "Result", "type": "float3"}]},
            ],
            "connections": [
                {"source_node": "CurveInput", "source_pin": "Curve", "target_node": "Sample", "target_pin": "Curve"},
                {"source_node": "Sample", "source_pin": "Value", "target_node": "ApplyScale", "target_pin": "B"},
            ],
            "hlsl_expressions": [],
        }

        with patch("unreal_niagara_mcp.analysis.hlsl_output_tools._call_plugin", return_value=graph_data):
            graph_result = get_module_graph("/Niagara/Modules/ScaleOverLife")

        assert "Nodes (3)" in graph_result
        assert "SampleCurve: Sample" in graph_result
        assert "CurveInput.Curve -> Sample.Curve" in graph_result

        # Step 2: User wants to know what functions the curve DI provides
        di_data = {
            "class_name": "NiagaraDataInterfaceCurve",
            "functions": [
                {
                    "name": "SampleCurve",
                    "return_type": "float",
                    "parameters": [
                        {"name": "Time", "type": "float", "direction": "in"},
                    ],
                    "description": "Sample the curve at the given normalized time",
                },
            ],
        }

        with patch("unreal_niagara_mcp.analysis.hlsl_output_tools._call_plugin", return_value=di_data):
            di_result = get_di_functions("NiagaraDataInterfaceCurve")

        assert "float SampleCurve(float Time)" in di_result
        assert "Sample the curve" in di_result


# ===========================================================================
# Workflow 5: Scalability + pooling audit
# ===========================================================================


class TestScalabilityPoolingWorkflow:
    """Simulates: audit scalability -> audit pooling -> batch fix."""

    def test_scalability_then_pooling(self):
        from unreal_niagara_mcp.analysis.stats_tools import audit_scalability
        from unreal_niagara_mcp.analysis.audit_tools import audit_pooling

        mock_bridge = MagicMock()

        # Step 1: Scalability audit
        scalability_data = {
            "asset_path": "/Game/VFX/NS_Impact",
            "system_settings": {
                "effect_type": None,
                "warmup_time": 0.0,
            },
            "emitters": [
                {
                    "name": "Debris",
                    "sim_target": "CPUSim",
                    "bounds_mode": "Auto",
                    "has_scalability_overrides": False,
                },
            ],
            "recommendations": [
                "No effect type set - consider assigning one for scalability budgets",
                "Emitter 'Debris' has no scalability overrides",
                "Emitter 'Debris' uses Auto bounds - consider Fixed for performance",
            ],
        }

        # Step 2: Pooling audit
        pooling_data = {
            "asset_path": "/Game/VFX/NS_Impact",
            "pool_method": "None",
            "pool_prime_size": 0,
            "auto_deactivate": False,
            "uses_pooling": False,
            "emitter_count": 1,
            "has_burst_spawn": True,
            "has_continuous_spawn": False,
            "recommendations": [
                "System uses burst spawning - good candidate for pooling",
                "Recommended pool size: 4-8 instances",
            ],
        }

        mock_bridge.run_command.side_effect = [
            _make_bridge_result(scalability_data),
            _make_bridge_result(pooling_data),
        ]

        with patch("unreal_niagara_mcp.analysis.stats_tools._get_bridge", return_value=mock_bridge), \
             patch("unreal_niagara_mcp.analysis.audit_tools._get_bridge", return_value=mock_bridge):

            scal_result = audit_scalability("/Game/VFX/NS_Impact")
            assert "No effect type set" in scal_result
            assert "no scalability overrides" in scal_result

            pool_result = audit_pooling("/Game/VFX/NS_Impact")
            assert "good candidate for pooling" in pool_result
            assert "Recommended pool size: 4-8" in pool_result


# ===========================================================================
# Workflow 6: HLSL output inspection
# ===========================================================================


class TestHLSLInspectionWorkflow:
    """Simulates: get emitter summary -> get HLSL output."""

    def test_summary_then_hlsl(self):
        from unreal_niagara_mcp.analysis.summary_tools import get_emitter_summary
        from unreal_niagara_mcp.analysis.dream_tools import get_hlsl_output

        mock_bridge = MagicMock()

        # Step 1: Summary reveals GPU emitter
        summary_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "emitter": {
                "name": "Sparks",
                "is_enabled": True,
                "sim_target": "GPUComputeSim",
                "local_space": False,
                "bounds_mode": "Fixed",
                "modules": {
                    "particle_spawn": ["SpawnBurst"],
                    "particle_update": ["Gravity", "ColorOverLife"],
                },
                "renderers": [
                    {"class": "NiagaraSpriteRendererProperties", "material": "M_Spark", "is_enabled": True},
                ],
            },
        }

        mock_bridge.run_command.return_value = _make_bridge_result(summary_data)

        with patch("unreal_niagara_mcp.analysis.summary_tools._get_bridge", return_value=mock_bridge):
            summary_result = get_emitter_summary("/Game/VFX/NS_Fire", "Sparks")

        assert "GPU" in summary_result

        # Step 2: Get compiled HLSL
        hlsl_data = {
            "emitter_name": "Sparks",
            "compile_status": "Success",
            "hlsl": "void SimulateMain()\n{\n  // GPU sim code\n}\n",
        }

        with patch("unreal_niagara_mcp.analysis.dream_tools._call_plugin", return_value=hlsl_data):
            hlsl_result = get_hlsl_output("/Game/VFX/NS_Fire", "Sparks")

        assert "SimulateMain" in hlsl_result
        assert "Compile Status: Success" in hlsl_result
