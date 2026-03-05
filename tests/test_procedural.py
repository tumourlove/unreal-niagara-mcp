"""Tests for Niagara procedural tools -- curves and distributions are pure math."""

import json
import math
from unittest.mock import MagicMock, patch

import pytest

from unreal_niagara_mcp.server import _reset_state


@pytest.fixture(autouse=True)
def reset():
    _reset_state()
    yield
    _reset_state()


# ---------------------------------------------------------------------------
# curve_tools -- pure math tests
# ---------------------------------------------------------------------------


class TestGenerateCurveKeys:

    def test_linear_curve(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("linear", 0.0, 1.0, num_keys=5, amplitude=1.0)
        assert len(keys) == 5
        assert keys[0]["value"] == pytest.approx(0.0, abs=0.001)
        assert keys[-1]["value"] == pytest.approx(1.0, abs=0.001)
        # Linear curve: midpoint should be ~0.5
        assert keys[2]["value"] == pytest.approx(0.5, abs=0.001)

    def test_ease_in_starts_slow(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("ease_in", 0.0, 1.0, num_keys=5)
        # At t=0.25, ease_in = 0.25^2 = 0.0625
        assert keys[1]["value"] == pytest.approx(0.0625, abs=0.001)

    def test_ease_out_starts_fast(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("ease_out", 0.0, 1.0, num_keys=5)
        # At t=0.25, ease_out = 1-(0.75^2) = 0.4375
        assert keys[1]["value"] == pytest.approx(0.4375, abs=0.001)

    def test_sine_wave(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("sine", 0.0, 1.0, num_keys=5, frequency=1.0)
        # At t=0.25, sin(0.25 * 2pi) = sin(pi/2) = 1.0
        assert keys[1]["value"] == pytest.approx(1.0, abs=0.001)
        # At t=0.5, sin(pi) ~ 0
        assert keys[2]["value"] == pytest.approx(0.0, abs=0.001)

    def test_bell_curve_peaks_at_center(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("bell_curve", 0.0, 1.0, num_keys=11)
        # Peak at t=0.5 (index 5 of 11)
        center = keys[5]["value"]
        edge = keys[0]["value"]
        assert center > edge

    def test_step_function(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("step", 0.0, 1.0, num_keys=5)
        assert keys[0]["value"] == pytest.approx(0.0)
        assert keys[1]["value"] == pytest.approx(0.0)  # t=0.25 < 0.5
        assert keys[3]["value"] == pytest.approx(1.0)  # t=0.75 >= 0.5
        assert keys[4]["value"] == pytest.approx(1.0)

    def test_amplitude_scaling(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("linear", 0.0, 1.0, num_keys=3, amplitude=5.0)
        assert keys[-1]["value"] == pytest.approx(5.0, abs=0.01)

    def test_custom_expression(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("custom", 0.0, 1.0, num_keys=3, custom_expression="t * t")
        # t=0: 0, t=0.5: 0.25, t=1: 1
        assert keys[0]["value"] == pytest.approx(0.0, abs=0.001)
        assert keys[1]["value"] == pytest.approx(0.25, abs=0.001)
        assert keys[2]["value"] == pytest.approx(1.0, abs=0.001)

    def test_custom_with_trig(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("custom", 0.0, 1.0, num_keys=3, custom_expression="sin(t * pi)")
        # t=0: 0, t=0.5: sin(pi/2)=1, t=1: sin(pi)~0
        assert keys[0]["value"] == pytest.approx(0.0, abs=0.01)
        assert keys[1]["value"] == pytest.approx(1.0, abs=0.01)
        assert keys[2]["value"] == pytest.approx(0.0, abs=0.01)

    def test_custom_missing_expression(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        with pytest.raises(ValueError, match="custom_expression is required"):
            generate_curve_keys("custom", 0.0, 1.0, num_keys=3)

    def test_unknown_function_type(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        with pytest.raises(ValueError, match="Unknown function type"):
            generate_curve_keys("nonexistent", 0.0, 1.0, num_keys=3)

    def test_tangents_computed(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("linear", 0.0, 1.0, num_keys=5)
        # Linear curve should have ~constant tangent
        for k in keys:
            assert "arrive_tangent" in k
            assert "leave_tangent" in k
            assert k["arrive_tangent"] == pytest.approx(1.0, abs=0.1)

    def test_minimum_keys(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_keys

        keys = generate_curve_keys("linear", 0.0, 1.0, num_keys=1)
        assert len(keys) == 2  # Minimum enforced


class TestGenerateCurveFromFunctionTool:

    def test_tool_returns_string_with_json(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_from_function

        result = generate_curve_from_function("linear", num_keys=3)
        assert "Curve: linear" in result
        assert "JSON Keys" in result
        # Should contain parseable JSON after "--- JSON Keys ---"
        json_marker = result.index("--- JSON Keys ---")
        json_start = result.index("[", json_marker)
        json_str = result[json_start:]
        keys = json.loads(json_str)
        assert len(keys) == 3

    def test_tool_handles_error(self):
        from unreal_niagara_mcp.procedural.curve_tools import generate_curve_from_function

        result = generate_curve_from_function("nonexistent")
        assert "Error" in result


# ---------------------------------------------------------------------------
# distribution_tools -- pure math tests
# ---------------------------------------------------------------------------


class TestFibonacciSphere:

    def test_correct_count(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _fibonacci_sphere

        points = _fibonacci_sphere(100, 50.0)
        assert len(points) == 100

    def test_points_on_sphere(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _fibonacci_sphere

        points = _fibonacci_sphere(50, 100.0)
        for p in points:
            dist = math.sqrt(p[0] ** 2 + p[1] ** 2 + p[2] ** 2)
            assert dist == pytest.approx(100.0, abs=0.1)


class TestPhyllotaxisDisk:

    def test_correct_count(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _phyllotaxis_disk

        points = _phyllotaxis_disk(50, 100.0)
        assert len(points) == 50

    def test_z_is_zero(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _phyllotaxis_disk

        points = _phyllotaxis_disk(20, 50.0)
        for p in points:
            assert p[2] == 0.0

    def test_within_radius(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _phyllotaxis_disk

        points = _phyllotaxis_disk(50, 100.0)
        for p in points:
            dist = math.sqrt(p[0] ** 2 + p[1] ** 2)
            assert dist <= 100.1  # small tolerance


class TestCubeSurface:

    def test_correct_count(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _cube_surface

        points = _cube_surface(24, 50.0)
        assert len(points) == 24


class TestGoldenSpiral:

    def test_correct_count(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _golden_spiral

        points = _golden_spiral(30, 100.0)
        assert len(points) == 30

    def test_starts_at_origin(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _golden_spiral

        points = _golden_spiral(10, 100.0)
        dist = math.sqrt(sum(c ** 2 for c in points[0]))
        assert dist == pytest.approx(0.0, abs=0.1)


class TestPoissonDisk:

    def test_produces_points(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _poisson_disk

        points = _poisson_disk(20, 100.0)
        assert len(points) > 0
        assert len(points) <= 20

    def test_within_radius(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _poisson_disk

        points = _poisson_disk(15, 50.0)
        for p in points:
            dist = math.sqrt(p[0] ** 2 + p[1] ** 2)
            assert dist <= 50.1


class TestAttractor:

    def test_correct_count(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _attractor

        points = _attractor(50, 100.0)
        assert len(points) == 50

    def test_points_are_3d(self):
        from unreal_niagara_mcp.procedural.distribution_tools import _attractor

        points = _attractor(10, 100.0)
        for p in points:
            assert len(p) == 3


class TestCreateParticleDistributionTool:

    def test_returns_formatted_output(self):
        from unreal_niagara_mcp.procedural.distribution_tools import create_particle_distribution

        result = create_particle_distribution("fibonacci_sphere", count=10, radius=50.0)

        assert "Particle Distribution: fibonacci_sphere" in result
        assert "Count: 10" in result
        assert "Bounding Box:" in result
        assert "Preview" in result
        assert "JSON Positions" in result

    def test_unknown_type(self):
        from unreal_niagara_mcp.procedural.distribution_tools import create_particle_distribution

        result = create_particle_distribution("nonexistent")
        assert "Unknown distribution type" in result

    def test_json_output_parseable(self):
        from unreal_niagara_mcp.procedural.distribution_tools import create_particle_distribution

        result = create_particle_distribution("phyllotaxis_disk", count=5, radius=10.0)
        # Extract JSON from output
        json_marker = "--- JSON Positions ---\n"
        json_start = result.index(json_marker) + len(json_marker)
        json_str = result[json_start:]
        positions = json.loads(json_str)
        assert len(positions) == 5
        assert len(positions[0]) == 3


# ---------------------------------------------------------------------------
# hlsl_tools
# ---------------------------------------------------------------------------


class TestGenerateModuleHlsl:

    def test_generates_default_module(self):
        from unreal_niagara_mcp.procedural.hlsl_tools import generate_module_hlsl

        result = generate_module_hlsl("Apply gravity to particles")

        assert "Generated HLSL Module" in result
        assert "SimulateMain" in result
        assert "DeltaTime" in result
        assert "InputMap" in result
        assert "OutputMap" in result

    def test_generates_with_custom_inputs(self):
        from unreal_niagara_mcp.procedural.hlsl_tools import generate_module_hlsl

        inputs = json.dumps([
            {"name": "Speed", "type": "float", "default": "1.0"},
            {"name": "Direction", "type": "float3"},
        ])
        outputs = json.dumps([
            {"name": "Force", "type": "float3"},
        ])

        result = generate_module_hlsl("Custom force module", inputs=inputs, outputs=outputs)

        assert "Speed" in result
        assert "Direction" in result
        assert "Force" in result
        assert "Inputs: 2" in result
        assert "Outputs: 1" in result

    def test_invalid_inputs_json(self):
        from unreal_niagara_mcp.procedural.hlsl_tools import generate_module_hlsl

        result = generate_module_hlsl("Test", inputs="not json")
        assert "Error" in result
        assert "Invalid JSON" in result


class TestGenerateDynamicInputExpression:

    def test_sine_wave(self):
        from unreal_niagara_mcp.procedural.hlsl_tools import generate_dynamic_input_expression

        result = generate_dynamic_input_expression("sine_wave")
        assert "sine_wave" in result
        assert "sin" in result
        assert "Expression" in result

    def test_with_custom_params(self):
        from unreal_niagara_mcp.procedural.hlsl_tools import generate_dynamic_input_expression

        params = json.dumps({"amplitude": "5.0", "frequency": "2.0"})
        result = generate_dynamic_input_expression("sine_wave", parameters=params)
        assert "5.0" in result
        assert "2.0" in result
        assert "(custom)" in result

    def test_unknown_type(self):
        from unreal_niagara_mcp.procedural.hlsl_tools import generate_dynamic_input_expression

        result = generate_dynamic_input_expression("nonexistent")
        assert "Unknown expression type" in result

    def test_all_expression_types(self):
        from unreal_niagara_mcp.procedural.hlsl_tools import generate_dynamic_input_expression, _EXPRESSION_TEMPLATES

        for expr_type in _EXPRESSION_TEMPLATES:
            result = generate_dynamic_input_expression(expr_type)
            assert "Expression" in result, f"Failed for type: {expr_type}"


# ---------------------------------------------------------------------------
# system_gen_tools
# ---------------------------------------------------------------------------


class TestCreateProceduralSystem:

    def test_creates_from_spec(self):
        from unreal_niagara_mcp.procedural.system_gen_tools import create_procedural_system

        spec = json.dumps({
            "name": "NS_Test",
            "save_path": "/Game/VFX/NS_Test",
            "emitters": [
                {
                    "name": "Main",
                    "sim_target": "GPU",
                    "modules": {"particle_update": ["/Niagara/Modules/GravityForce"]},
                    "renderers": [{"class": "sprite"}],
                }
            ],
            "user_parameters": [{"name": "Intensity", "type": "float", "default": 1.0}],
        })

        mock_data = {"success": True}
        with patch("unreal_niagara_mcp.procedural.system_gen_tools._call_plugin", return_value=mock_data):
            result = create_procedural_system(spec)

        assert "NS_Test" in result
        assert "Main" in result
        assert "Intensity" in result
        assert "unsaved" in result

    def test_invalid_json(self):
        from unreal_niagara_mcp.procedural.system_gen_tools import create_procedural_system

        result = create_procedural_system("not valid json")
        assert "Error" in result

    def test_missing_save_path(self):
        from unreal_niagara_mcp.procedural.system_gen_tools import create_procedural_system

        result = create_procedural_system(json.dumps({"name": "test"}))
        assert "Error" in result
        assert "save_path" in result


class TestCreateSimStageSetup:

    def test_applies_recipe(self):
        from unreal_niagara_mcp.procedural.system_gen_tools import create_sim_stage_setup

        mock_data = {"success": True}
        with patch("unreal_niagara_mcp.procedural.system_gen_tools._call_plugin", return_value=mock_data):
            result = create_sim_stage_setup("/Game/VFX/NS_Fluid", "FluidEmitter", "fluid_2d")

        assert "fluid_2d" in result
        assert "PressureSolve" in result
        assert "Advection" in result
        assert "Grid2DCollection" in result
        assert "128" in result

    def test_unknown_recipe(self):
        from unreal_niagara_mcp.procedural.system_gen_tools import create_sim_stage_setup

        result = create_sim_stage_setup("/Game/VFX/NS_Test", "Main", "nonexistent")
        assert "Unknown recipe" in result
        assert "fluid_2d" in result  # Lists available


class TestSpecToBatchOps:

    def test_converts_simple_spec(self):
        from unreal_niagara_mcp.procedural.system_gen_tools import _spec_to_batch_ops

        spec = {
            "save_path": "/Game/VFX/NS_Test",
            "emitters": [
                {
                    "name": "Main",
                    "modules": {
                        "particle_update": [
                            {"path": "/Niagara/Modules/GravityForce", "inputs": {"Gravity": "-500"}},
                        ]
                    },
                    "renderers": [{"class": "sprite", "material": "/Game/M_Test"}],
                }
            ],
            "user_parameters": [{"name": "Scale", "type": "float", "default": "1.0"}],
        }

        ops = _spec_to_batch_ops(spec)
        op_types = [o["op"] for o in ops]

        assert "create_system" in op_types
        assert "add_emitter" in op_types
        assert "add_module" in op_types
        assert "set_input" in op_types
        assert "add_renderer" in op_types
        assert "add_user_parameter" in op_types


# ---------------------------------------------------------------------------
# variation_tools
# ---------------------------------------------------------------------------


class TestGenerateEffectVariations:

    def test_generates_variations(self):
        from unreal_niagara_mcp.procedural.variation_tools import generate_effect_variations

        dup_data = {"success": True, "path": "/Game/VFX/NS_Fire_Var01"}
        mod_data = {"success": True}

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = {
            "success": True,
            "output": json.dumps(dup_data),
        }

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge), \
             patch("unreal_niagara_mcp.procedural.variation_tools._call_plugin", return_value=mod_data):
            result = generate_effect_variations("/Game/VFX/NS_Fire", "scale_range", count=3)

        assert "scale_range" in result
        assert "Created: 3" in result
        assert "Var01" in result

    def test_unknown_variation_type(self):
        from unreal_niagara_mcp.procedural.variation_tools import generate_effect_variations

        result = generate_effect_variations("/Game/VFX/NS_Test", "nonexistent")
        assert "Unknown variation type" in result


class TestVariationStrategies:

    def test_color_shift_varies_hue(self):
        from unreal_niagara_mcp.procedural.variation_tools import _compute_color_shift_params

        p0 = _compute_color_shift_params(0, 3, {})
        p1 = _compute_color_shift_params(1, 3, {})
        p2 = _compute_color_shift_params(2, 3, {})
        assert p0["hue_offset"] == 0.0
        assert p1["hue_offset"] == pytest.approx(120.0, abs=0.1)
        assert p2["hue_offset"] == pytest.approx(240.0, abs=0.1)

    def test_scale_range(self):
        from unreal_niagara_mcp.procedural.variation_tools import _compute_scale_params

        p0 = _compute_scale_params(0, 3, {"min_scale": "1.0", "max_scale": "3.0"})
        p2 = _compute_scale_params(2, 3, {"min_scale": "1.0", "max_scale": "3.0"})
        assert p0["scale_factor"] == pytest.approx(1.0, abs=0.01)
        assert p2["scale_factor"] == pytest.approx(3.0, abs=0.01)

    def test_combined_has_all_keys(self):
        from unreal_niagara_mcp.procedural.variation_tools import _compute_combined_params

        p = _compute_combined_params(0, 3, {})
        assert "hue_offset" in p
        assert "scale_factor" in p
        assert "speed_multiplier" in p
        assert "density_multiplier" in p
