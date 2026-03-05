"""Niagara system and emitter inspection tools using UPROPERTY reads."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _escape_py_string, _format_error


# ---------------------------------------------------------------------------
# get_niagara_system_info
# ---------------------------------------------------------------------------

_SYSTEM_INFO_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    handles = system.get_editor_property("emitter_handles")
    info = {{
        "asset_path": path,
        "emitter_count": len(handles) if handles else 0,
        "warmup_time": system.get_editor_property("warmup_time"),
        "warmup_tick_count": system.get_editor_property("warmup_tick_count"),
        "warmup_tick_delta": system.get_editor_property("warmup_tick_delta"),
        "determinism": system.get_editor_property("determinism"),
        "fixed_tick_delta": system.get_editor_property("fixed_tick_delta"),
        "fixed_tick_delta_time": system.get_editor_property("fixed_tick_delta_time"),
    }}
    print(json.dumps(info))
'''


@mcp.tool()
def get_niagara_system_info(asset_path: str) -> str:
    """Get overview info for a Niagara system: emitter count, warmup, determinism, tick settings.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    """
    bridge = _get_bridge()
    escaped = _escape_py_string(asset_path)
    command = _SYSTEM_INFO_SCRIPT.format(asset_path=escaped)

    try:
        result = bridge.run_command(command, exec_mode="ExecuteFile")
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    if not result.get("success", False):
        return f"Error: {result.get('result', 'Command failed')}"

    import json
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
        data = json.loads(output)
    except json.JSONDecodeError:
        return f"Error: Invalid response from editor: {output[:300]}"

    err = _format_error(data)
    if err:
        return err

    lines = [
        f"Niagara System: {data.get('asset_path', '')}",
        f"  Emitter Count: {data.get('emitter_count', 0)}",
        "",
        "Warmup Settings:",
        f"  Warmup Time: {data.get('warmup_time', 0.0)}",
        f"  Warmup Tick Count: {data.get('warmup_tick_count', 0)}",
        f"  Warmup Tick Delta: {data.get('warmup_tick_delta', 0.0)}",
        "",
        "Tick Settings:",
        f"  Determinism: {data.get('determinism', False)}",
        f"  Fixed Tick Delta: {data.get('fixed_tick_delta', False)}",
        f"  Fixed Tick Delta Time: {data.get('fixed_tick_delta_time', 0.0)}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# get_niagara_emitters
# ---------------------------------------------------------------------------

_EMITTERS_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    handles = system.get_editor_property("emitter_handles")
    emitters = []
    if handles:
        for h in handles:
            name = h.get_editor_property("name")
            is_enabled = h.get_editor_property("is_enabled")
            emitter_inst = h.get_editor_property("instance")
            em_data = {{
                "name": str(name) if name else "Unknown",
                "is_enabled": bool(is_enabled),
            }}
            if emitter_inst is not None:
                ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    sim_target = latest.get_editor_property("sim_target")
                    em_data["sim_target"] = str(sim_target) if sim_target is not None else "Unknown"
                    local_space = latest.get_editor_property("local_space")
                    em_data["local_space"] = bool(local_space) if local_space is not None else False
                    try:
                        bounds_mode = latest.get_editor_property("calculation_bounds_mode")
                        em_data["bounds_mode"] = str(bounds_mode) if bounds_mode is not None else "Unknown"
                    except Exception:
                        em_data["bounds_mode"] = "Unknown"
                    try:
                        renderers = latest.get_editor_property("renderer_properties")
                        em_data["renderer_count"] = len(renderers) if renderers else 0
                    except Exception:
                        em_data["renderer_count"] = 0
            emitters.append(em_data)
    print(json.dumps({{"asset_path": path, "emitters": emitters}}))
'''


@mcp.tool()
def get_niagara_emitters(asset_path: str) -> str:
    """List all emitters in a Niagara system with key properties.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    """
    bridge = _get_bridge()
    escaped = _escape_py_string(asset_path)
    command = _EMITTERS_SCRIPT.format(asset_path=escaped)

    try:
        result = bridge.run_command(command, exec_mode="ExecuteFile")
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    if not result.get("success", False):
        return f"Error: {result.get('result', 'Command failed')}"

    import json
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
        data = json.loads(output)
    except json.JSONDecodeError:
        return f"Error: Invalid response from editor: {output[:300]}"

    err = _format_error(data)
    if err:
        return err

    emitters = data.get("emitters", [])
    if not emitters:
        return f"System {data.get('asset_path', '')} has no emitters."

    lines = [f"Niagara System: {data.get('asset_path', '')}", f"Emitters ({len(emitters)}):", ""]
    for i, em in enumerate(emitters):
        enabled = "Enabled" if em.get("is_enabled", True) else "Disabled"
        lines.append(f"  [{i}] {em.get('name', '?')} ({enabled})")
        if "sim_target" in em:
            lines.append(f"      Sim Target: {em['sim_target']}")
        if "local_space" in em:
            lines.append(f"      Local Space: {em['local_space']}")
        if "bounds_mode" in em:
            lines.append(f"      Bounds Mode: {em['bounds_mode']}")
        if "renderer_count" in em:
            lines.append(f"      Renderers: {em['renderer_count']}")
        lines.append("")

    return "\n".join(lines).rstrip()
