"""Built-in preset recipes for common Niagara VFX patterns.

Each preset is a declarative specification that can be translated into
batch operations for the C++ plugin's BatchExecute function.
"""

from __future__ import annotations

PRESETS: dict[str, dict] = {
    "burst_sprite": {
        "description": "Single burst of sprite particles with gravity and fade-out.",
        "emitters": [
            {
                "name": "Burst",
                "sim_target": "CPU",
                "modules": {
                    "emitter_spawn": [
                        "/Niagara/Modules/SpawnBurstInstantaneous",
                    ],
                    "particle_spawn": [
                        "/Niagara/Modules/InitializeParticle",
                        "/Niagara/Modules/AddVelocityInCone",
                    ],
                    "particle_update": [
                        "/Niagara/Modules/GravityForce",
                        "/Niagara/Modules/SolveForcesAndVelocity",
                        "/Niagara/Modules/ScaleColorOverLife",
                        "/Niagara/Modules/ScaleSpriteSize",
                    ],
                },
                "renderers": [{"class": "sprite"}],
                "default_inputs": {
                    "SpawnBurstInstantaneous.SpawnCount": "20",
                    "AddVelocityInCone.ConeAngle": "45.0",
                    "AddVelocityInCone.Speed": "200.0",
                },
            }
        ],
    },
    "continuous_sprite": {
        "description": "Continuous stream of sprite particles with velocity and drag.",
        "emitters": [
            {
                "name": "Stream",
                "sim_target": "CPU",
                "modules": {
                    "emitter_spawn": [],
                    "emitter_update": [
                        "/Niagara/Modules/SpawnRate",
                    ],
                    "particle_spawn": [
                        "/Niagara/Modules/InitializeParticle",
                        "/Niagara/Modules/AddVelocityInCone",
                    ],
                    "particle_update": [
                        "/Niagara/Modules/Drag",
                        "/Niagara/Modules/SolveForcesAndVelocity",
                        "/Niagara/Modules/ScaleColorOverLife",
                        "/Niagara/Modules/ScaleSpriteSize",
                    ],
                },
                "renderers": [{"class": "sprite"}],
                "default_inputs": {
                    "SpawnRate.SpawnRate": "50.0",
                    "AddVelocityInCone.ConeAngle": "30.0",
                    "AddVelocityInCone.Speed": "150.0",
                    "Drag.Drag": "2.0",
                },
            }
        ],
    },
    "trail_ribbon": {
        "description": "Ribbon trail effect with color gradient and width curve.",
        "emitters": [
            {
                "name": "Trail",
                "sim_target": "CPU",
                "modules": {
                    "emitter_update": [
                        "/Niagara/Modules/SpawnRate",
                    ],
                    "particle_spawn": [
                        "/Niagara/Modules/InitializeParticle",
                    ],
                    "particle_update": [
                        "/Niagara/Modules/SolveForcesAndVelocity",
                        "/Niagara/Modules/ScaleColorOverLife",
                    ],
                },
                "renderers": [{"class": "ribbon"}],
                "default_inputs": {
                    "SpawnRate.SpawnRate": "30.0",
                },
            }
        ],
    },
    "mesh_emitter": {
        "description": "Static mesh particle emitter with rotation and scaling.",
        "emitters": [
            {
                "name": "Meshes",
                "sim_target": "CPU",
                "modules": {
                    "emitter_spawn": [
                        "/Niagara/Modules/SpawnBurstInstantaneous",
                    ],
                    "particle_spawn": [
                        "/Niagara/Modules/InitializeParticle",
                        "/Niagara/Modules/AddVelocityInCone",
                        "/Niagara/Modules/InitialMeshOrientation",
                    ],
                    "particle_update": [
                        "/Niagara/Modules/GravityForce",
                        "/Niagara/Modules/SolveForcesAndVelocity",
                        "/Niagara/Modules/MeshRotationForce",
                        "/Niagara/Modules/ScaleMeshSize",
                    ],
                },
                "renderers": [{"class": "mesh"}],
                "default_inputs": {
                    "SpawnBurstInstantaneous.SpawnCount": "10",
                    "MeshRotationForce.RotationRate": "180.0",
                },
            }
        ],
    },
    "gpu_particles": {
        "description": "High-count GPU particle system with noise-based movement.",
        "emitters": [
            {
                "name": "GPUParticles",
                "sim_target": "GPU",
                "modules": {
                    "emitter_update": [
                        "/Niagara/Modules/SpawnRate",
                    ],
                    "particle_spawn": [
                        "/Niagara/Modules/InitializeParticle",
                        "/Niagara/Modules/AddVelocityInCone",
                    ],
                    "particle_update": [
                        "/Niagara/Modules/CurlNoiseForce",
                        "/Niagara/Modules/SolveForcesAndVelocity",
                        "/Niagara/Modules/ScaleColorOverLife",
                        "/Niagara/Modules/ScaleSpriteSize",
                    ],
                },
                "renderers": [{"class": "sprite"}],
                "default_inputs": {
                    "SpawnRate.SpawnRate": "5000.0",
                    "CurlNoiseForce.NoiseLacunarity": "2.0",
                },
            }
        ],
    },
    "impact_radial": {
        "description": "Radial burst for impact effects with debris and dust.",
        "emitters": [
            {
                "name": "Debris",
                "sim_target": "CPU",
                "modules": {
                    "emitter_spawn": [
                        "/Niagara/Modules/SpawnBurstInstantaneous",
                    ],
                    "particle_spawn": [
                        "/Niagara/Modules/InitializeParticle",
                        "/Niagara/Modules/AddVelocityFromPoint",
                    ],
                    "particle_update": [
                        "/Niagara/Modules/GravityForce",
                        "/Niagara/Modules/SolveForcesAndVelocity",
                        "/Niagara/Modules/ScaleSpriteSize",
                    ],
                },
                "renderers": [{"class": "sprite"}],
                "default_inputs": {
                    "SpawnBurstInstantaneous.SpawnCount": "30",
                    "AddVelocityFromPoint.Speed": "300.0",
                },
            },
            {
                "name": "Dust",
                "sim_target": "CPU",
                "modules": {
                    "emitter_spawn": [
                        "/Niagara/Modules/SpawnBurstInstantaneous",
                    ],
                    "particle_spawn": [
                        "/Niagara/Modules/InitializeParticle",
                        "/Niagara/Modules/AddVelocityFromPoint",
                    ],
                    "particle_update": [
                        "/Niagara/Modules/Drag",
                        "/Niagara/Modules/SolveForcesAndVelocity",
                        "/Niagara/Modules/ScaleColorOverLife",
                        "/Niagara/Modules/ScaleSpriteSize",
                    ],
                },
                "renderers": [{"class": "sprite"}],
                "default_inputs": {
                    "SpawnBurstInstantaneous.SpawnCount": "15",
                    "AddVelocityFromPoint.Speed": "100.0",
                    "Drag.Drag": "5.0",
                },
            },
        ],
    },
    "ambient_loop": {
        "description": "Looping ambient particles for environmental effects.",
        "emitters": [
            {
                "name": "Ambient",
                "sim_target": "CPU",
                "modules": {
                    "emitter_update": [
                        "/Niagara/Modules/SpawnRate",
                    ],
                    "particle_spawn": [
                        "/Niagara/Modules/InitializeParticle",
                        "/Niagara/Modules/ShapeLocation",
                    ],
                    "particle_update": [
                        "/Niagara/Modules/WindForce",
                        "/Niagara/Modules/SolveForcesAndVelocity",
                        "/Niagara/Modules/ScaleColorOverLife",
                        "/Niagara/Modules/ScaleSpriteSize",
                    ],
                },
                "renderers": [{"class": "sprite"}],
                "default_inputs": {
                    "SpawnRate.SpawnRate": "10.0",
                    "ShapeLocation.ShapeType": "Box",
                    "ShapeLocation.BoxSize": "500.0",
                },
            }
        ],
    },
}


def get_preset_names() -> list[str]:
    """Return all available preset names."""
    return sorted(PRESETS.keys())


def get_preset(name: str) -> dict | None:
    """Return a preset by name, or None if not found."""
    return PRESETS.get(name)


def preset_to_batch_ops(preset: dict, save_path: str) -> list[dict]:
    """Convert a preset definition to a list of batch operations for C++ BatchExecute.

    Returns a list of operation dicts suitable for JSON serialization.
    """
    ops: list[dict] = []

    # First op: create the system
    ops.append({
        "op": "create_system",
        "save_path": save_path,
    })

    for emitter_def in preset.get("emitters", []):
        emitter_name = emitter_def["name"]

        # Add emitter
        ops.append({
            "op": "add_emitter",
            "emitter_name": emitter_name,
            "sim_target": emitter_def.get("sim_target", "CPU"),
        })

        # Add modules per stage
        modules = emitter_def.get("modules", {})
        for stage, module_paths in modules.items():
            for module_path in module_paths:
                ops.append({
                    "op": "add_module",
                    "emitter_name": emitter_name,
                    "stage": stage,
                    "module_path": module_path,
                })

        # Set default inputs
        for input_key, input_val in emitter_def.get("default_inputs", {}).items():
            ops.append({
                "op": "set_input",
                "emitter_name": emitter_name,
                "input_key": input_key,
                "value": input_val,
            })

        # Add renderers
        for renderer_def in emitter_def.get("renderers", []):
            ops.append({
                "op": "add_renderer",
                "emitter_name": emitter_name,
                "renderer_class": renderer_def["class"],
            })

    return ops
