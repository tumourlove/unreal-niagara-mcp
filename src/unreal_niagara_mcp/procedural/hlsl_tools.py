"""Niagara HLSL code generation tools for custom modules and dynamic inputs."""

from __future__ import annotations

import json

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _call_plugin, _format_error


# ---------------------------------------------------------------------------
# HLSL Templates
# ---------------------------------------------------------------------------

_MODULE_TEMPLATE = """\
// Module: {name}
// {description}
//
// Inputs:
{input_comments}
// Outputs:
{output_comments}

void SimulateMain(in float DeltaTime, in int ExecutionIndex)
{{
    // Read inputs
{input_reads}

    // Compute
{body}

    // Write outputs
{output_writes}
}}
"""

_EXPRESSION_TEMPLATES: dict[str, dict] = {
    "sine_wave": {
        "description": "Oscillating sine wave",
        "params": ["amplitude", "frequency", "offset"],
        "defaults": {"amplitude": "1.0", "frequency": "1.0", "offset": "0.0"},
        "expression": "{amplitude} * sin(Engine.Time * {frequency} * 6.28318 + {offset})",
    },
    "noise": {
        "description": "Perlin-style noise value",
        "params": ["scale", "speed"],
        "defaults": {"scale": "1.0", "speed": "1.0"},
        "expression": "PerlinNoise3D(Particles.Position * {scale} + Engine.Time * {speed})",
    },
    "random_range": {
        "description": "Random value between min and max",
        "params": ["min_val", "max_val"],
        "defaults": {"min_val": "0.0", "max_val": "1.0"},
        "expression": "lerp({min_val}, {max_val}, RandomRange(0.0, 1.0))",
    },
    "lerp": {
        "description": "Linear interpolation over normalized age",
        "params": ["start_val", "end_val"],
        "defaults": {"start_val": "0.0", "end_val": "1.0"},
        "expression": "lerp({start_val}, {end_val}, Particles.NormalizedAge)",
    },
    "gradient": {
        "description": "Smooth gradient based on particle age",
        "params": ["power"],
        "defaults": {"power": "2.0"},
        "expression": "pow(1.0 - Particles.NormalizedAge, {power})",
    },
    "radial": {
        "description": "Radial distance from origin",
        "params": ["center_x", "center_y", "center_z", "falloff"],
        "defaults": {"center_x": "0.0", "center_y": "0.0", "center_z": "0.0", "falloff": "1.0"},
        "expression": (
            "saturate(1.0 - length(Particles.Position - float3({center_x}, {center_y}, {center_z})) "
            "* {falloff})"
        ),
    },
    "distance_fade": {
        "description": "Fade based on distance from a point",
        "params": ["fade_start", "fade_end"],
        "defaults": {"fade_start": "100.0", "fade_end": "500.0"},
        "expression": (
            "saturate((length(Particles.Position) - {fade_start}) / ({fade_end} - {fade_start}))"
        ),
    },
}


def _build_module_hlsl(
    name: str,
    description: str,
    inputs: list[dict] | None,
    outputs: list[dict] | None,
) -> str:
    """Build HLSL module code from a specification.

    Each input/output dict has: {"name": str, "type": str, "default": str (optional)}
    """
    inputs = inputs or [{"name": "InputValue", "type": "float", "default": "0.0"}]
    outputs = outputs or [{"name": "OutputValue", "type": "float"}]

    input_comments = "\n".join(
        f"//   {inp['type']} {inp['name']}" + (f" = {inp['default']}" if 'default' in inp else "")
        for inp in inputs
    )
    output_comments = "\n".join(f"//   {out['type']} {out['name']}" for out in outputs)

    input_reads = "\n".join(
        f"    {inp['type']} {inp['name']} = InputMap.{inp['name']};"
        for inp in inputs
    )
    output_writes = "\n".join(
        f"    OutputMap.{out['name']} = {out['name']};"
        for out in outputs
    )

    # Generate a simple placeholder body
    body_lines = []
    for out in outputs:
        if out["type"] == "float":
            if inputs:
                body_lines.append(f"    float {out['name']} = {inputs[0]['name']};")
            else:
                body_lines.append(f"    float {out['name']} = 0.0;")
        elif out["type"] in ("float2", "float3", "float4"):
            body_lines.append(f"    {out['type']} {out['name']} = ({out['type']})0;")
        elif out["type"] == "bool":
            body_lines.append(f"    bool {out['name']} = true;")
        else:
            body_lines.append(f"    {out['type']} {out['name']} = ({out['type']})0;")
    body = "\n".join(body_lines) if body_lines else "    // TODO: implement computation"

    return _MODULE_TEMPLATE.format(
        name=name,
        description=description,
        input_comments=input_comments,
        output_comments=output_comments,
        input_reads=input_reads,
        body=body,
        output_writes=output_writes,
    )


@mcp.tool()
def generate_module_hlsl(
    description: str,
    inputs: str = "",
    outputs: str = "",
    create_asset: bool = False,
    save_path: str = "",
) -> str:
    """Generate HLSL code for a Niagara module with proper conventions.

    Produces a SimulateMain function with input reads and output writes
    following Niagara module conventions. Optionally creates the module
    asset in the editor.

    description: What the module does (used as code comment and module name)
    inputs: JSON array of inputs, e.g. '[{"name":"Speed","type":"float","default":"1.0"}]'
    outputs: JSON array of outputs, e.g. '[{"name":"Force","type":"float3"}]'
    create_asset: If True, create the module asset in the editor via C++ plugin
    save_path: Required if create_asset is True, e.g. '/Game/VFX/Modules/MyModule'
    """
    # Parse inputs/outputs from JSON strings
    parsed_inputs = None
    parsed_outputs = None
    if inputs:
        try:
            parsed_inputs = json.loads(inputs)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON for inputs: {inputs[:200]}"
    if outputs:
        try:
            parsed_outputs = json.loads(outputs)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON for outputs: {outputs[:200]}"

    # Derive a module name from description
    name = description.replace(" ", "_")[:40]

    hlsl_code = _build_module_hlsl(name, description, parsed_inputs, parsed_outputs)

    lines = [
        "Generated HLSL Module",
        f"  Name: {name}",
        f"  Inputs: {len(parsed_inputs or [])}",
        f"  Outputs: {len(parsed_outputs or [])}",
        "",
        "--- HLSL Code ---",
        hlsl_code,
    ]

    if create_asset:
        if not save_path:
            lines.append("Warning: create_asset=True but no save_path provided. Asset not created.")
        else:
            try:
                data = _call_plugin(
                    "NiagaraModuleLibrary",
                    "CreateModuleFromHLSL",
                    SavePath=save_path,
                    HLSLCode=hlsl_code,
                )
            except EditorNotRunning as e:
                lines.append(f"\nAsset creation failed: Editor not available: {e}")
                return "\n".join(lines)

            err = _format_error(data)
            if err:
                lines.append(f"\nAsset creation failed: {err}")
            else:
                lines.append(f"\nAsset Created: {data.get('asset_path', save_path)}")
                lines.append("Status: Asset created (unsaved)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# generate_dynamic_input_expression
# ---------------------------------------------------------------------------


@mcp.tool()
def generate_dynamic_input_expression(
    expression_type: str,
    parameters: str = "",
) -> str:
    """Generate HLSL expressions for Niagara dynamic inputs.

    Returns an HLSL expression string suitable for pasting into a
    Niagara dynamic input field.

    Available types: sine_wave, noise, random_range, lerp, gradient,
    radial, distance_fade.

    expression_type: Type of expression to generate
    parameters: JSON object of parameter overrides, e.g. '{"amplitude":"2.0","frequency":"0.5"}'
    """
    template = _EXPRESSION_TEMPLATES.get(expression_type)
    if template is None:
        available = ", ".join(sorted(_EXPRESSION_TEMPLATES.keys()))
        return f"Unknown expression type '{expression_type}'. Available: {available}"

    # Parse parameter overrides
    overrides = {}
    if parameters:
        try:
            overrides = json.loads(parameters)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON for parameters: {parameters[:200]}"

    # Merge defaults with overrides
    params = dict(template["defaults"])
    params.update(overrides)

    # Generate expression
    try:
        expression = template["expression"].format(**params)
    except KeyError as e:
        return f"Error: Missing parameter {e}. Required: {', '.join(template['params'])}"

    lines = [
        f"Dynamic Input Expression: {expression_type}",
        f"  Description: {template['description']}",
        "",
        "Parameters:",
    ]
    for p in template["params"]:
        val = params.get(p, "?")
        default = template["defaults"].get(p, "?")
        marker = " (custom)" if p in overrides else ""
        lines.append(f"  {p} = {val}{marker}  [default: {default}]")

    lines.extend([
        "",
        "--- Expression ---",
        expression,
    ])

    return "\n".join(lines)
