"""Niagara system and emitter creation tools."""

from __future__ import annotations

import json

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import (
    mcp,
    _get_bridge,
    _call_plugin,
    _escape_py_string,
    _format_error,
)
from unreal_niagara_mcp.search.search_tools import _run_bridge_script
from unreal_niagara_mcp.creation.preset_tools import (
    PRESETS,
    get_preset,
    get_preset_names,
    preset_to_batch_ops,
)


# ---------------------------------------------------------------------------
# create_niagara_system
# ---------------------------------------------------------------------------


@mcp.tool()
def create_niagara_system(
    save_path: str,
    template_path: str = "",
) -> str:
    """Create a new Niagara system, optionally from a template.

    The asset is created but NOT saved — it remains dirty for the user to save.

    save_path: Where to save the system, e.g. '/Game/VFX/NS_MyEffect'
    template_path: Optional template system to base it on
    """
    try:
        kwargs = {"SavePath": save_path}
        if template_path:
            kwargs["TemplatePath"] = template_path
        data = _call_plugin("NiagaraSystemLibrary", "CreateNiagaraSystem", **kwargs)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    lines = [
        f"Created Niagara System",
        f"  Path: {data.get('asset_path', save_path)}",
    ]
    if template_path:
        lines.append(f"  Template: {template_path}")
    lines.append("  Status: Asset created (unsaved)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# create_niagara_emitter
# ---------------------------------------------------------------------------

_CREATE_EMITTER_SCRIPT = '''\
import unreal, json
save_path = "{save_path}"
template_path = "{template_path}"
sim_target = "{sim_target}"
try:
    parts = save_path.rsplit("/", 1)
    if len(parts) != 2:
        print(json.dumps({{"error": True, "message": "Invalid save_path format"}}))
    else:
        package_path, asset_name = parts
        if template_path:
            source = unreal.load_asset(template_path)
            if source is None:
                print(json.dumps({{"error": True, "message": f"Template not found: {{template_path}}"}}))
            else:
                result = unreal.EditorAssetLibrary.duplicate_asset(template_path, save_path)
                if result:
                    print(json.dumps({{"asset_path": save_path}}))
                else:
                    print(json.dumps({{"error": True, "message": "Failed to duplicate template"}}))
        else:
            factory = unreal.NiagaraEmitterFactory()
            asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
            emitter = asset_tools.create_asset(asset_name, package_path, None, factory)
            if emitter is not None:
                if sim_target == "gpu":
                    emitter.set_editor_property("sim_target", unreal.ENiagaraSimTarget.GPUCOMPUTE_SIM)
                print(json.dumps({{"asset_path": emitter.get_path_name()}}))
            else:
                print(json.dumps({{"error": True, "message": "Failed to create emitter asset"}}))
except Exception as e:
    print(json.dumps({{"error": True, "message": str(e)}}))
'''


@mcp.tool()
def create_niagara_emitter(
    save_path: str,
    template_path: str = "",
    sim_target: str = "cpu",
) -> str:
    """Create a standalone Niagara emitter asset.

    The asset is created but NOT saved — it remains dirty for the user to save.

    save_path: Where to save the emitter, e.g. '/Game/VFX/Emitters/NE_MyEmitter'
    template_path: Optional template emitter to duplicate from
    sim_target: 'cpu' or 'gpu' (default: 'cpu')
    """
    if sim_target not in ("cpu", "gpu"):
        return "Error: sim_target must be 'cpu' or 'gpu'"

    escaped_save = _escape_py_string(save_path)
    escaped_template = _escape_py_string(template_path)
    script = _CREATE_EMITTER_SCRIPT.format(
        save_path=escaped_save,
        template_path=escaped_template,
        sim_target=sim_target,
    )

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    lines = [
        f"Created Niagara Emitter",
        f"  Path: {data.get('asset_path', save_path)}",
    ]
    if template_path:
        lines.append(f"  Template: {template_path}")
    lines.append(f"  Sim Target: {sim_target.upper()}")
    lines.append("  Status: Asset created (unsaved)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# create_niagara_module
# ---------------------------------------------------------------------------


@mcp.tool()
def create_niagara_module(
    save_path: str,
    inputs: str = "",
    outputs: str = "",
    hlsl_code: str = "",
    description: str = "",
) -> str:
    """Create a Niagara module script asset with HLSL code.

    If hlsl_code is not provided, a template module is generated from
    the inputs/outputs specification.

    save_path: Where to save the module, e.g. '/Game/VFX/Modules/MyModule'
    inputs: JSON array of inputs, e.g. '[{"name":"Speed","type":"float","default":"1.0"}]'
    outputs: JSON array of outputs, e.g. '[{"name":"Force","type":"float3"}]'
    hlsl_code: Optional raw HLSL code (if empty, code is auto-generated)
    description: Optional description for the module
    """
    from unreal_niagara_mcp.procedural.hlsl_tools import _build_module_hlsl

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

    if not hlsl_code:
        name = (description or "CustomModule").replace(" ", "_")[:40]
        hlsl_code = _build_module_hlsl(name, description or "Custom module", parsed_inputs, parsed_outputs)

    try:
        kwargs = {"SavePath": save_path, "HLSLCode": hlsl_code}
        if inputs:
            kwargs["InputsJson"] = inputs
        if outputs:
            kwargs["OutputsJson"] = outputs
        data = _call_plugin("NiagaraModuleLibrary", "CreateModuleFromHLSL", **kwargs)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    lines = [
        "Created Niagara Module",
        f"  Path: {data.get('asset_path', save_path)}",
        f"  Inputs: {len(parsed_inputs or [])}",
        f"  Outputs: {len(parsed_outputs or [])}",
        "  Status: Asset created (unsaved)",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# create_niagara_function
# ---------------------------------------------------------------------------


@mcp.tool()
def create_niagara_function(
    save_path: str,
    inputs: str,
    outputs: str,
    hlsl_code: str,
) -> str:
    """Create a Niagara function script asset from HLSL code.

    save_path: Where to save the function, e.g. '/Game/VFX/Functions/MyFunc'
    inputs: JSON array of inputs, e.g. '[{"name":"Value","type":"float"}]'
    outputs: JSON array of outputs, e.g. '[{"name":"Result","type":"float"}]'
    hlsl_code: The HLSL code for the function body
    """
    # Validate JSON
    try:
        parsed_inputs = json.loads(inputs)
    except json.JSONDecodeError:
        return f"Error: Invalid JSON for inputs: {inputs[:200]}"
    try:
        parsed_outputs = json.loads(outputs)
    except json.JSONDecodeError:
        return f"Error: Invalid JSON for outputs: {outputs[:200]}"

    try:
        data = _call_plugin(
            "NiagaraModuleLibrary",
            "CreateFunctionFromHLSL",
            SavePath=save_path,
            HLSLCode=hlsl_code,
            InputsJson=inputs,
            OutputsJson=outputs,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    lines = [
        "Created Niagara Function",
        f"  Path: {data.get('asset_path', save_path)}",
        f"  Inputs: {len(parsed_inputs)}",
        f"  Outputs: {len(parsed_outputs)}",
        "  Status: Asset created (unsaved)",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# duplicate_niagara_system
# ---------------------------------------------------------------------------

_DUPLICATE_SCRIPT = '''\
import unreal, json
source = "{source_path}"
dest = "{save_path}"
result = unreal.EditorAssetLibrary.duplicate_asset(source, dest)
if result:
    print(json.dumps({{"success": True, "source": source, "destination": dest}}))
else:
    print(json.dumps({{"error": True, "message": f"Failed to duplicate {{source}} to {{dest}}"}}))
'''


@mcp.tool()
def duplicate_niagara_system(source_path: str, save_path: str) -> str:
    """Duplicate an existing Niagara system to a new asset path.

    source_path: Path of the system to duplicate
    save_path: Destination path for the copy
    """
    escaped_source = _escape_py_string(source_path)
    escaped_dest = _escape_py_string(save_path)
    script = _DUPLICATE_SCRIPT.format(source_path=escaped_source, save_path=escaped_dest)

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Duplicated Niagara System\n"
        f"  Source: {data.get('source', source_path)}\n"
        f"  Destination: {data.get('destination', save_path)}"
    )


# ---------------------------------------------------------------------------
# duplicate_emitter
# ---------------------------------------------------------------------------


@mcp.tool()
def duplicate_emitter(
    asset_path: str,
    source_emitter_name: str,
    new_name: str,
) -> str:
    """Duplicate an emitter within a Niagara system.

    asset_path: System containing the emitter
    source_emitter_name: Name of the emitter to duplicate
    new_name: Name for the new copy
    """
    try:
        data = _call_plugin(
            "NiagaraEmitterLibrary",
            "DuplicateEmitter",
            AssetPath=asset_path,
            SourceEmitterName=source_emitter_name,
            NewName=new_name,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Duplicated Emitter\n"
        f"  System: {asset_path}\n"
        f"  Source: {source_emitter_name}\n"
        f"  New Emitter: {data.get('new_name', new_name)}\n"
        f"  Status: Asset modified (unsaved)"
    )


# ---------------------------------------------------------------------------
# clone_emitter_between_systems
# ---------------------------------------------------------------------------


@mcp.tool()
def clone_emitter_between_systems(
    source_system: str,
    source_emitter: str,
    target_system: str,
    new_name: str = "",
) -> str:
    """Clone an emitter from one system to another.

    source_system: System to copy the emitter from
    source_emitter: Name of the emitter to copy
    target_system: System to add the emitter to
    new_name: Optional name for the cloned emitter (defaults to source name)
    """
    try:
        kwargs = {
            "SourceSystem": source_system,
            "SourceEmitter": source_emitter,
            "TargetSystem": target_system,
        }
        if new_name:
            kwargs["NewName"] = new_name
        data = _call_plugin("NiagaraEmitterLibrary", "AddEmitter", **kwargs)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    actual_name = data.get("emitter_name", new_name or source_emitter)
    return (
        f"Cloned Emitter\n"
        f"  From: {source_system} / {source_emitter}\n"
        f"  To: {target_system} / {actual_name}\n"
        f"  Status: Target system modified (unsaved)"
    )


# ---------------------------------------------------------------------------
# create_from_preset
# ---------------------------------------------------------------------------


@mcp.tool()
def create_from_preset(save_path: str, preset_name: str) -> str:
    """Create a Niagara system from a built-in preset recipe.

    Available presets: burst_sprite, continuous_sprite, trail_ribbon,
    mesh_emitter, gpu_particles, impact_radial, ambient_loop.

    Each preset defines emitters, modules, renderers, and default inputs
    to create a ready-to-use VFX system.

    save_path: Where to save the system, e.g. '/Game/VFX/NS_MyBurst'
    preset_name: Name of the preset to use
    """
    preset = get_preset(preset_name)
    if preset is None:
        available = ", ".join(get_preset_names())
        return f"Unknown preset '{preset_name}'. Available: {available}"

    batch_ops = preset_to_batch_ops(preset, save_path)
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

    emitter_names = [e["name"] for e in preset.get("emitters", [])]
    lines = [
        f"Created from Preset: {preset_name}",
        f"  Description: {preset.get('description', '')}",
        f"  Path: {save_path}",
        f"  Emitters: {', '.join(emitter_names)}",
        f"  Operations: {len(batch_ops)}",
        f"  Status: Asset created (unsaved)",
    ]

    return "\n".join(lines)
