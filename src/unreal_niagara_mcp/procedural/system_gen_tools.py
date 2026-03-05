"""Procedural Niagara system generation tools."""

from __future__ import annotations

import json

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _call_plugin, _format_error


# ---------------------------------------------------------------------------
# Sim stage recipes
# ---------------------------------------------------------------------------

_SIM_STAGE_RECIPES: dict[str, dict] = {
    "fluid_2d": {
        "description": "2D fluid simulation using Grid2D data interface.",
        "stages": [
            {
                "name": "PressureSolve",
                "iteration_count": 20,
                "data_interface": "Grid2DCollection",
                "modules": [
                    "/Niagara/Modules/Grid2D/PressureProjection",
                ],
            },
            {
                "name": "Advection",
                "iteration_count": 1,
                "data_interface": "Grid2DCollection",
                "modules": [
                    "/Niagara/Modules/Grid2D/Advection",
                    "/Niagara/Modules/Grid2D/ApplyBoundary",
                ],
            },
        ],
        "grid_config": {
            "resolution_x": 128,
            "resolution_y": 128,
            "world_size": 500.0,
        },
    },
    "fluid_3d": {
        "description": "3D fluid simulation using Grid3D data interface.",
        "stages": [
            {
                "name": "PressureSolve",
                "iteration_count": 20,
                "data_interface": "Grid3DCollection",
                "modules": [
                    "/Niagara/Modules/Grid3D/PressureProjection",
                ],
            },
            {
                "name": "Advection",
                "iteration_count": 1,
                "data_interface": "Grid3DCollection",
                "modules": [
                    "/Niagara/Modules/Grid3D/Advection",
                    "/Niagara/Modules/Grid3D/ApplyBoundary",
                ],
            },
        ],
        "grid_config": {
            "resolution_x": 64,
            "resolution_y": 64,
            "resolution_z": 64,
            "world_size": 500.0,
        },
    },
    "flocking": {
        "description": "Flocking/boids behaviour with neighbor search.",
        "stages": [
            {
                "name": "NeighborSearch",
                "iteration_count": 1,
                "data_interface": "NeighborGrid3D",
                "modules": [
                    "/Niagara/Modules/NeighborGrid3D/PopulateGrid",
                ],
            },
            {
                "name": "FlockingForces",
                "iteration_count": 1,
                "data_interface": "NeighborGrid3D",
                "modules": [
                    "/Niagara/Modules/NeighborGrid3D/QueryNeighbors",
                ],
            },
        ],
        "grid_config": {
            "max_neighbors": 16,
            "cell_size": 50.0,
            "world_size": 2000.0,
        },
    },
    "sdf_collision": {
        "description": "Signed distance field collision response.",
        "stages": [
            {
                "name": "SDFCollision",
                "iteration_count": 1,
                "data_interface": "DistanceField",
                "modules": [
                    "/Niagara/Modules/SDF/QueryDistance",
                    "/Niagara/Modules/SDF/CollisionResponse",
                ],
            },
        ],
        "grid_config": {},
    },
    "neighbor_search": {
        "description": "Generic neighbor search for interaction-based effects.",
        "stages": [
            {
                "name": "BuildGrid",
                "iteration_count": 1,
                "data_interface": "NeighborGrid3D",
                "modules": [
                    "/Niagara/Modules/NeighborGrid3D/PopulateGrid",
                ],
            },
            {
                "name": "QueryNeighbors",
                "iteration_count": 1,
                "data_interface": "NeighborGrid3D",
                "modules": [
                    "/Niagara/Modules/NeighborGrid3D/QueryNeighbors",
                ],
            },
        ],
        "grid_config": {
            "max_neighbors": 8,
            "cell_size": 100.0,
            "world_size": 1000.0,
        },
    },
}


def _spec_to_batch_ops(spec: dict) -> list[dict]:
    """Convert a declarative system spec to batch operations."""
    ops: list[dict] = []
    save_path = spec.get("save_path", "/Game/VFX/NS_Procedural")

    ops.append({
        "op": "create_system",
        "save_path": save_path,
    })

    for emitter_def in spec.get("emitters", []):
        emitter_name = emitter_def.get("name", "Emitter")

        # Add emitter (optionally from template)
        add_op: dict = {
            "op": "add_emitter",
            "emitter_name": emitter_name,
        }
        if "template" in emitter_def:
            add_op["template_path"] = emitter_def["template"]
        if "sim_target" in emitter_def:
            add_op["sim_target"] = emitter_def["sim_target"]
        ops.append(add_op)

        # Add modules per stage
        modules = emitter_def.get("modules", {})
        for stage, module_list in modules.items():
            for module_entry in module_list:
                if isinstance(module_entry, str):
                    ops.append({
                        "op": "add_module",
                        "emitter_name": emitter_name,
                        "stage": stage,
                        "module_path": module_entry,
                    })
                elif isinstance(module_entry, dict):
                    ops.append({
                        "op": "add_module",
                        "emitter_name": emitter_name,
                        "stage": stage,
                        "module_path": module_entry["path"],
                    })
                    # Set inputs for this module
                    for input_key, input_val in module_entry.get("inputs", {}).items():
                        ops.append({
                            "op": "set_input",
                            "emitter_name": emitter_name,
                            "input_key": input_key,
                            "value": str(input_val),
                        })

        # Add renderers
        for renderer_def in emitter_def.get("renderers", []):
            add_r: dict = {
                "op": "add_renderer",
                "emitter_name": emitter_name,
                "renderer_class": renderer_def.get("class", "sprite"),
            }
            if "material" in renderer_def:
                add_r["material"] = renderer_def["material"]
            ops.append(add_r)

    # Add user parameters
    for param in spec.get("user_parameters", []):
        ops.append({
            "op": "add_user_parameter",
            "name": param["name"],
            "type": param["type"],
            "default": str(param.get("default", "")),
        })

    return ops


@mcp.tool()
def create_procedural_system(spec: str) -> str:
    """Create a Niagara system from a declarative JSON specification.

    The spec describes the complete system: emitters, modules, renderers,
    and user parameters. It gets translated to batch operations executed
    by the C++ plugin.

    Spec format example:
    {
      "name": "NS_ProceduralFire",
      "save_path": "/Game/VFX/NS_ProceduralFire",
      "emitters": [
        {
          "name": "Flames",
          "sim_target": "GPU",
          "modules": {
            "particle_update": [
              {"path": "/Niagara/Modules/GravityForce", "inputs": {"Gravity": "-500"}}
            ]
          },
          "renderers": [{"class": "sprite", "material": "/Game/M_Fire"}]
        }
      ],
      "user_parameters": [{"name": "Intensity", "type": "float", "default": 1.0}]
    }

    spec: JSON string describing the system
    """
    try:
        spec_dict = json.loads(spec)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON spec: {e}"

    if "save_path" not in spec_dict:
        return "Error: spec must include 'save_path'"

    batch_ops = _spec_to_batch_ops(spec_dict)
    ops_json = json.dumps(batch_ops)

    try:
        data = _call_plugin(
            "NiagaraBatchLibrary",
            "BatchExecute",
            Operations=ops_json,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    emitter_names = [e.get("name", "?") for e in spec_dict.get("emitters", [])]
    param_names = [p.get("name", "?") for p in spec_dict.get("user_parameters", [])]

    lines = [
        f"Created Procedural System: {spec_dict.get('name', 'Unnamed')}",
        f"  Path: {spec_dict['save_path']}",
        f"  Emitters: {', '.join(emitter_names) if emitter_names else '(none)'}",
        f"  User Parameters: {', '.join(param_names) if param_names else '(none)'}",
        f"  Batch Operations: {len(batch_ops)}",
        f"  Status: Asset created (unsaved)",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# create_sim_stage_setup
# ---------------------------------------------------------------------------


@mcp.tool()
def create_sim_stage_setup(
    asset_path: str,
    emitter_name: str,
    recipe_name: str,
) -> str:
    """Set up simulation stages on an emitter using a predefined recipe.

    Recipes configure advanced simulation features like fluid sim, flocking,
    or neighbor search with appropriate data interfaces and module stacks.

    Available recipes: fluid_2d, fluid_3d, flocking, sdf_collision, neighbor_search.

    asset_path: System containing the emitter
    emitter_name: Emitter to configure
    recipe_name: Simulation recipe to apply
    """
    recipe = _SIM_STAGE_RECIPES.get(recipe_name)
    if recipe is None:
        available = ", ".join(sorted(_SIM_STAGE_RECIPES.keys()))
        return f"Unknown recipe '{recipe_name}'. Available: {available}"

    # Build batch operations for sim stage setup
    ops: list[dict] = []

    # Configure grid/DI
    grid_config = recipe.get("grid_config", {})
    if grid_config:
        ops.append({
            "op": "configure_data_interface",
            "asset_path": asset_path,
            "emitter_name": emitter_name,
            "config": grid_config,
        })

    # Add sim stages
    for stage in recipe.get("stages", []):
        ops.append({
            "op": "add_sim_stage",
            "asset_path": asset_path,
            "emitter_name": emitter_name,
            "stage_name": stage["name"],
            "iteration_count": stage.get("iteration_count", 1),
            "data_interface": stage.get("data_interface", ""),
        })
        for module_path in stage.get("modules", []):
            ops.append({
                "op": "add_module",
                "emitter_name": emitter_name,
                "stage": stage["name"],
                "module_path": module_path,
            })

    ops_json = json.dumps(ops)

    try:
        data = _call_plugin(
            "NiagaraBatchLibrary",
            "BatchExecute",
            Operations=ops_json,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    stages = recipe.get("stages", [])
    lines = [
        f"Sim Stage Setup: {recipe_name}",
        f"  Description: {recipe.get('description', '')}",
        f"  System: {asset_path}",
        f"  Emitter: {emitter_name}",
        f"  Stages: {len(stages)}",
        "",
    ]
    for s in stages:
        lines.append(f"  Stage: {s['name']}")
        lines.append(f"    Iterations: {s.get('iteration_count', 1)}")
        lines.append(f"    Data Interface: {s.get('data_interface', 'none')}")
        lines.append(f"    Modules: {len(s.get('modules', []))}")
        for m in s.get("modules", []):
            lines.append(f"      - {m}")

    if grid_config:
        lines.append("")
        lines.append("  Grid Config:")
        for k, v in grid_config.items():
            lines.append(f"    {k}: {v}")

    lines.append("")
    lines.append("  Status: Emitter modified (unsaved)")

    return "\n".join(lines)
