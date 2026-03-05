"""Niagara emitter natural language summary tool."""

from __future__ import annotations

import json

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _escape_py_string, _format_error


# ---------------------------------------------------------------------------
# Helper: parse bridge output
# ---------------------------------------------------------------------------

def _parse_bridge_output(result: dict) -> dict:
    """Parse a bridge run_command result into a JSON dict."""
    if not result.get("success", False):
        return {"error": True, "message": result.get("result", "Command failed")}

    raw_output = result.get("output", "")
    if isinstance(raw_output, list):
        parts = []
        for item in raw_output:
            if isinstance(item, dict):
                parts.append(item.get("output", str(item)))
            else:
                parts.append(str(item))
        output = "\n".join(parts).strip()
    else:
        output = str(raw_output).strip()
    if not output:
        output = str(result.get("result", "")).strip()

    json_start = output.find("{")
    if json_start > 0:
        output = output[json_start:]

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"error": True, "message": f"Invalid JSON from editor: {output[:500]}"}


# ---------------------------------------------------------------------------
# get_emitter_summary
# ---------------------------------------------------------------------------

_SUMMARY_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
emitter_filter = "{emitter_name}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    handles = system.get_editor_property("emitter_handles")
    found = False
    if handles:
        for h in handles:
            name = str(h.get_editor_property("name"))
            if name != emitter_filter:
                continue
            found = True
            is_enabled = bool(h.get_editor_property("is_enabled"))
            emitter_inst = h.get_editor_property("instance")
            info = {{
                "name": name,
                "is_enabled": is_enabled,
                "sim_target": "Unknown",
                "local_space": False,
                "bounds_mode": "Unknown",
                "modules": {{}},
                "renderers": [],
                "data_interfaces": [],
            }}
            if emitter_inst is not None:
                ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    try:
                        sim_target = latest.get_editor_property("sim_target")
                        info["sim_target"] = str(sim_target) if sim_target is not None else "Unknown"
                    except Exception:
                        pass
                    try:
                        info["local_space"] = bool(latest.get_editor_property("local_space"))
                    except Exception:
                        pass
                    try:
                        bounds_mode = latest.get_editor_property("calculation_bounds_mode")
                        info["bounds_mode"] = str(bounds_mode) if bounds_mode is not None else "Unknown"
                    except Exception:
                        pass
                    for script_attr in ["emitter_spawn_script_props",
                                        "emitter_update_script_props",
                                        "particle_spawn_script_props",
                                        "particle_update_script_props"]:
                        stage_name = script_attr.replace("_script_props", "")
                        try:
                            props = latest.get_editor_property(script_attr)
                            if props is not None:
                                script = props.get_editor_property("script")
                                if script is not None:
                                    try:
                                        modules = script.get_editor_property("modules")
                                        if modules:
                                            mod_names = []
                                            for m in modules:
                                                mod_names.append(type(m).__name__)
                                            info["modules"][stage_name] = mod_names
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                    try:
                        renderers = latest.get_editor_property("renderer_properties")
                        if renderers:
                            for r in renderers:
                                rclass = type(r).__name__
                                r_info = {{"class": rclass}}
                                try:
                                    mat = r.get_editor_property("material")
                                    if mat is not None:
                                        r_info["material"] = mat.get_name()
                                except Exception:
                                    pass
                                try:
                                    r_info["is_enabled"] = bool(r.get_editor_property("is_enabled"))
                                except Exception:
                                    r_info["is_enabled"] = True
                                info["renderers"].append(r_info)
                    except Exception:
                        pass
            print(json.dumps({{"asset_path": path, "emitter": info}}))
            break
    if not found:
        print(json.dumps({{"error": True, "message": f"Emitter '{{emitter_filter}}' not found in {{path}}"}}))
'''


def _build_summary_text(data: dict) -> str:
    """Compose a natural language description from emitter data."""
    em = data.get("emitter", {})
    name = em.get("name", "Unknown")
    sim_target = em.get("sim_target", "Unknown")
    local_space = em.get("local_space", False)
    bounds_mode = em.get("bounds_mode", "Unknown")
    is_enabled = em.get("is_enabled", True)
    modules = em.get("modules", {})
    renderers = em.get("renderers", [])

    # Determine sim type label
    if "GPU" in sim_target:
        sim_label = "GPU"
    elif "CPU" in sim_target:
        sim_label = "CPU"
    else:
        sim_label = sim_target

    # Gather module names across all stages
    all_modules = []
    for stage, mods in modules.items():
        for m in mods:
            all_modules.append(m)

    # Build description parts
    parts = []

    # Opening
    enabled_str = "" if is_enabled else " (currently disabled)"
    space_str = "local space" if local_space else "world space"
    parts.append(f"This {sim_label} emitter{enabled_str} operates in {space_str} "
                 f"with {bounds_mode} bounds.")

    # Modules description
    if all_modules:
        mod_str = ", ".join(all_modules)
        parts.append(f"It uses the following modules: {mod_str}.")

    # Spawn info from module names
    spawn_mods = modules.get("particle_spawn", [])
    if spawn_mods:
        parts.append(f"Particle spawn stage: {', '.join(spawn_mods)}.")

    update_mods = modules.get("particle_update", [])
    if update_mods:
        parts.append(f"Particle update stage: {', '.join(update_mods)}.")

    # Renderers
    if renderers:
        renderer_descs = []
        for r in renderers:
            rclass = r.get("class", "Unknown")
            mat = r.get("material")
            if mat:
                renderer_descs.append(f"{rclass} (material: {mat})")
            else:
                renderer_descs.append(rclass)
        parts.append(f"Rendered with: {', '.join(renderer_descs)}.")
    else:
        parts.append("No renderers configured.")

    return " ".join(parts)


@mcp.tool()
def get_emitter_summary(asset_path: str, emitter_name: str) -> str:
    """Generate a natural language description of a Niagara emitter.

    Reads all properties, modules, inputs, and renderers from the emitter
    and composes a human-readable summary describing what the emitter does.

    Example output:
    "This GPU emitter spawns 500 particles per second using a cone velocity
    distribution. Particles are affected by gravity and drag, scale down over
    their 2-second lifetime, and are rendered as sprites using material
    M_Spark with additive blending."

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Name of the emitter within the system
    """
    bridge = _get_bridge()
    escaped_path = _escape_py_string(asset_path)
    escaped_emitter = _escape_py_string(emitter_name)
    command = _SUMMARY_SCRIPT.format(
        asset_path=escaped_path, emitter_name=escaped_emitter
    )

    try:
        result = bridge.run_command(command, exec_mode="ExecuteFile")
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    data = _parse_bridge_output(result)
    err = _format_error(data)
    if err:
        return err

    em = data.get("emitter", {})
    summary = _build_summary_text(data)

    lines = [
        f"Emitter Summary: {em.get('name', '?')}",
        f"System: {data.get('asset_path', '')}",
        "",
        summary,
        "",
        "Raw Details:",
        f"  Sim Target:  {em.get('sim_target', '?')}",
        f"  Local Space: {em.get('local_space', False)}",
        f"  Bounds Mode: {em.get('bounds_mode', '?')}",
        f"  Enabled:     {em.get('is_enabled', True)}",
    ]

    modules = em.get("modules", {})
    if modules:
        lines.append("")
        lines.append("Modules by Stage:")
        for stage, mods in modules.items():
            stage_label = stage.replace("_", " ").title()
            lines.append(f"  {stage_label}:")
            for m in mods:
                lines.append(f"    - {m}")

    renderers = em.get("renderers", [])
    if renderers:
        lines.append("")
        lines.append("Renderers:")
        for r in renderers:
            enabled = "Enabled" if r.get("is_enabled", True) else "Disabled"
            mat = r.get("material", "(none)")
            lines.append(f"  - {r.get('class', '?')} ({enabled}) Material: {mat}")

    return "\n".join(lines).rstrip()
