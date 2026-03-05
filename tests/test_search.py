"""Tests for Niagara search and discovery tools."""

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
    """Create a successful bridge.run_command() return value."""
    return {
        "success": True,
        "output": json.dumps(data),
    }


def _make_error_result(message: str) -> dict:
    return {
        "success": True,
        "output": json.dumps({"error": True, "message": message}),
    }


# ---------------------------------------------------------------------------
# search_niagara_systems
# ---------------------------------------------------------------------------


class TestSearchNiagaraSystems:

    def test_returns_formatted_system_list(self):
        from unreal_niagara_mcp.search.search_tools import search_niagara_systems

        mock_data = {
            "count": 3,
            "systems": [
                "/Game/VFX/NS_Fire.NS_Fire",
                "/Game/VFX/NS_Smoke.NS_Smoke",
                "/Game/VFX/NS_Sparks.NS_Sparks",
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = search_niagara_systems()

        assert "Niagara Systems (3)" in result
        assert "[0] /Game/VFX/NS_Fire.NS_Fire" in result
        assert "[2] /Game/VFX/NS_Sparks.NS_Sparks" in result

    def test_returns_no_results_message(self):
        from unreal_niagara_mcp.search.search_tools import search_niagara_systems

        mock_data = {"count": 0, "systems": []}
        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = search_niagara_systems(filter_text="nonexistent")

        assert "No Niagara systems found" in result

    def test_handles_editor_not_running(self):
        from unreal_niagara_mcp.search.search_tools import search_niagara_systems
        from unreal_niagara_mcp.editor_bridge import EditorNotRunning

        mock_bridge = MagicMock()
        mock_bridge.run_command.side_effect = EditorNotRunning("No editor")

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = search_niagara_systems()

        assert "Editor not available" in result


# ---------------------------------------------------------------------------
# search_niagara_modules
# ---------------------------------------------------------------------------


class TestSearchNiagaraModules:

    def test_returns_module_list(self):
        from unreal_niagara_mcp.search.search_tools import search_niagara_modules

        mock_data = {
            "count": 2,
            "modules": [
                "/Niagara/Modules/SpawnRate.SpawnRate",
                "/Niagara/Modules/GravityForce.GravityForce",
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = search_niagara_modules()

        assert "Niagara Modules (2)" in result
        assert "SpawnRate" in result
        assert "GravityForce" in result


# ---------------------------------------------------------------------------
# search_by_data_interface
# ---------------------------------------------------------------------------


class TestSearchByDataInterface:

    def test_returns_matching_systems(self):
        from unreal_niagara_mcp.search.search_tools import search_by_data_interface

        mock_data = {
            "di_class": "NiagaraDataInterfaceCurve",
            "count": 1,
            "systems": ["/Game/VFX/NS_Fire.NS_Fire"],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = search_by_data_interface("NiagaraDataInterfaceCurve")

        assert "NiagaraDataInterfaceCurve" in result
        assert "NS_Fire" in result

    def test_no_matches(self):
        from unreal_niagara_mcp.search.search_tools import search_by_data_interface

        mock_data = {"di_class": "NonExistent", "count": 0, "systems": []}

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = search_by_data_interface("NonExistent")

        assert "No systems found" in result


# ---------------------------------------------------------------------------
# search_by_parameter
# ---------------------------------------------------------------------------


class TestSearchByParameter:

    def test_returns_matching_systems(self):
        from unreal_niagara_mcp.search.search_tools import search_by_parameter

        mock_data = {
            "parameter_name": "Intensity",
            "count": 2,
            "systems": [
                {"path": "/Game/VFX/NS_Fire.NS_Fire", "param_name": "Intensity"},
                {"path": "/Game/VFX/NS_Glow.NS_Glow", "param_name": "GlowIntensity"},
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = search_by_parameter("Intensity")

        assert "Intensity" in result
        assert "NS_Fire" in result
        assert "NS_Glow" in result


# ---------------------------------------------------------------------------
# search_by_material
# ---------------------------------------------------------------------------


class TestSearchByMaterial:

    def test_returns_matching_systems(self):
        from unreal_niagara_mcp.search.search_tools import search_by_material

        mock_data = {
            "material": "/Game/Materials/M_Fire",
            "count": 1,
            "systems": ["/Game/VFX/NS_Fire.NS_Fire"],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = search_by_material("/Game/Materials/M_Fire")

        assert "M_Fire" in result
        assert "NS_Fire" in result


# ---------------------------------------------------------------------------
# find_niagara_references
# ---------------------------------------------------------------------------


class TestFindNiagaraReferences:

    def test_returns_references(self):
        from unreal_niagara_mcp.search.search_tools import find_niagara_references

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "referencers": ["/Game/Maps/Level1", "/Game/Blueprints/BP_Torch"],
            "referencer_count": 2,
            "dependencies": ["/Game/Materials/M_Fire"],
            "dependency_count": 1,
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = find_niagara_references("/Game/VFX/NS_Fire")

        assert "Referenced By (2)" in result
        assert "Level1" in result
        assert "BP_Torch" in result
        assert "Depends On (1)" in result
        assert "M_Fire" in result

    def test_no_references(self):
        from unreal_niagara_mcp.search.search_tools import find_niagara_references

        mock_data = {
            "asset_path": "/Game/VFX/NS_Orphan",
            "referencers": [],
            "referencer_count": 0,
            "dependencies": [],
            "dependency_count": 0,
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = find_niagara_references("/Game/VFX/NS_Orphan")

        assert "(none)" in result


# ---------------------------------------------------------------------------
# compare_niagara_systems
# ---------------------------------------------------------------------------


class TestCompareNiagaraSystems:

    def test_shows_differences(self):
        from unreal_niagara_mcp.search.search_tools import compare_niagara_systems

        mock_data = {
            "system_a": "/Game/VFX/NS_A",
            "system_b": "/Game/VFX/NS_B",
            "fingerprint_a": {
                "emitters": [
                    {"name": "Flames", "sim_target": "CPU", "modules": [], "renderers": ["SpriteRenderer"]},
                    {"name": "Sparks", "sim_target": "GPU", "modules": [], "renderers": ["SpriteRenderer"]},
                ],
                "parameters": ["Intensity", "Color"],
            },
            "fingerprint_b": {
                "emitters": [
                    {"name": "Flames", "sim_target": "GPU", "modules": [], "renderers": ["SpriteRenderer"]},
                    {"name": "Smoke", "sim_target": "CPU", "modules": [], "renderers": ["SpriteRenderer"]},
                ],
                "parameters": ["Intensity", "Scale"],
            },
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = compare_niagara_systems("/Game/VFX/NS_A", "/Game/VFX/NS_B")

        assert "System A: 2 emitter(s)" in result
        assert "System B: 2 emitter(s)" in result
        assert "Only in A:" in result
        assert "Sparks" in result
        assert "Only in B:" in result
        assert "Smoke" in result
        assert "Flames" in result
        assert "Color" in result
        assert "Scale" in result

    def test_handles_load_error(self):
        from unreal_niagara_mcp.search.search_tools import compare_niagara_systems

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_error_result("Cannot load system A")

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = compare_niagara_systems("/Game/VFX/NS_A", "/Game/VFX/NS_B")

        assert "Error" in result


# ---------------------------------------------------------------------------
# Discovery tools
# ---------------------------------------------------------------------------


class TestFindSimilarSystems:

    def test_returns_similar_systems(self):
        from unreal_niagara_mcp.search.discovery_tools import find_similar_systems

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "module_count": 5,
            "matches": [
                {"path": "/Game/VFX/NS_Torch", "similarity": 0.8},
                {"path": "/Game/VFX/NS_Campfire", "similarity": 0.6},
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = find_similar_systems("/Game/VFX/NS_Fire")

        assert "NS_Fire" in result
        assert "80.0%" in result
        assert "NS_Torch" in result
        assert "60.0%" in result

    def test_no_matches(self):
        from unreal_niagara_mcp.search.discovery_tools import find_similar_systems

        mock_data = {"asset_path": "/Game/VFX/NS_Unique", "module_count": 3, "matches": []}

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = find_similar_systems("/Game/VFX/NS_Unique")

        assert "No systems found" in result


class TestGetModuleUsageMap:

    def test_returns_usage_map(self):
        from unreal_niagara_mcp.search.discovery_tools import get_module_usage_map

        mock_data = {
            "systems_scanned": 10,
            "unique_modules": 3,
            "modules": [
                {"path": "/Niagara/Modules/SpawnRate", "count": 8},
                {"path": "/Niagara/Modules/GravityForce", "count": 5},
                {"path": "/Niagara/Modules/CurlNoise", "count": 2},
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = get_module_usage_map()

        assert "Systems scanned: 10" in result
        assert "Unique modules: 3" in result
        assert "SpawnRate" in result
        assert "8" in result


class TestGetNiagaraInventory:

    def test_returns_inventory(self):
        from unreal_niagara_mcp.search.discovery_tools import get_niagara_inventory

        mock_data = {
            "total_systems": 15,
            "total_emitters": 42,
            "gpu_emitters": 10,
            "cpu_emitters": 32,
            "unique_modules": 25,
            "unique_data_interfaces": 5,
            "renderer_types": {
                "NiagaraSpriteRendererProperties": 30,
                "NiagaraRibbonRendererProperties": 8,
                "NiagaraMeshRendererProperties": 4,
            },
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = get_niagara_inventory()

        assert "Total Systems:          15" in result
        assert "Total Emitters:         42" in result
        assert "GPU Emitters:         10" in result
        assert "CPU Emitters:         32" in result
        assert "NiagaraSpriteRendererProperties" in result


class TestQueryNiagara:

    def test_parses_and_filters(self):
        from unreal_niagara_mcp.search.discovery_tools import query_niagara

        mock_data = {
            "systems": [
                {"path": "/Game/VFX/NS_A", "emitter_count": 3, "sim_targets": ["GPUComputeSim"], "modules": [], "renderers": []},
                {"path": "/Game/VFX/NS_B", "emitter_count": 1, "sim_targets": ["CPUSim"], "modules": [], "renderers": []},
                {"path": "/Game/VFX/NS_C", "emitter_count": 5, "sim_targets": ["GPUComputeSim"], "modules": [], "renderers": []},
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = query_niagara("emitters>2 AND sim_target=GPU")

        assert "NS_A" in result
        assert "NS_C" in result
        assert "NS_B" not in result

    def test_invalid_query(self):
        from unreal_niagara_mcp.search.discovery_tools import query_niagara

        result = query_niagara("nonsense gibberish")
        assert "Could not parse" in result


class TestTraceEffectLineage:

    def test_returns_lineage(self):
        from unreal_niagara_mcp.search.discovery_tools import trace_effect_lineage

        mock_data = {
            "asset_path": "/Game/VFX/NS_Fire",
            "lineage": ["/Game/VFX/NS_Fire", "/Niagara/Templates/SimpleSprite"],
            "depth": 2,
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = trace_effect_lineage("/Game/VFX/NS_Fire")

        assert "Chain depth: 2" in result
        assert "(current)" in result
        assert "(template)" in result


class TestFindParameterConflicts:

    def test_returns_conflicts(self):
        from unreal_niagara_mcp.search.discovery_tools import find_parameter_conflicts

        mock_data = {
            "total_params_checked": 10,
            "conflicts": [
                {
                    "name": "Intensity",
                    "types": ["FloatProperty", "IntProperty"],
                    "entries": [
                        {"system": "/Game/VFX/NS_A", "type": "FloatProperty"},
                        {"system": "/Game/VFX/NS_B", "type": "IntProperty"},
                    ],
                }
            ],
        }

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = find_parameter_conflicts()

        assert "Conflicts found: 1" in result
        assert "Intensity" in result
        assert "FloatProperty" in result
        assert "IntProperty" in result

    def test_no_conflicts(self):
        from unreal_niagara_mcp.search.discovery_tools import find_parameter_conflicts

        mock_data = {"total_params_checked": 10, "conflicts": []}

        mock_bridge = MagicMock()
        mock_bridge.run_command.return_value = _make_bridge_result(mock_data)

        with patch("unreal_niagara_mcp.search.search_tools._get_bridge", return_value=mock_bridge):
            result = find_parameter_conflicts()

        assert "No parameter conflicts" in result
