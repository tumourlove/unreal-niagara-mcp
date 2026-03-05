"""Niagara renderer inspection tools using UPROPERTY reads."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _escape_py_string, _format_error


# ---------------------------------------------------------------------------
# get_niagara_renderers
# ---------------------------------------------------------------------------

_RENDERERS_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
emitter_filter = "{emitter_name}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    handles = system.get_editor_property("emitter_handles")
    result = {{"asset_path": path, "emitters": []}}
    if handles:
        for h in handles:
            name = str(h.get_editor_property("name"))
            if emitter_filter and name != emitter_filter:
                continue
            emitter_inst = h.get_editor_property("instance")
            renderers_out = []
            if emitter_inst is not None:
                ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    try:
                        renderers = latest.get_editor_property("renderer_properties")
                        if renderers:
                            for idx, r in enumerate(renderers):
                                rclass = type(r).__name__
                                r_info = {{
                                    "index": idx,
                                    "class": rclass,
                                    "is_enabled": True,
                                }}
                                try:
                                    r_info["is_enabled"] = bool(r.get_editor_property("is_enabled"))
                                except Exception:
                                    pass
                                try:
                                    r_info["sort_order_hint"] = int(r.get_editor_property("sort_order_hint"))
                                except Exception:
                                    pass
                                try:
                                    mat = r.get_editor_property("material")
                                    if mat is not None:
                                        r_info["material"] = mat.get_path_name()
                                    else:
                                        r_info["material"] = None
                                except Exception:
                                    pass
                                try:
                                    bindings = []
                                    for prop_name in ["position_binding", "color_binding",
                                                      "velocity_binding", "dynamic_material_binding",
                                                      "sprite_size_binding", "sprite_rotation_binding",
                                                      "mesh_index_binding", "ribbon_width_binding",
                                                      "ribbon_twist_binding"]:
                                        try:
                                            b = r.get_editor_property(prop_name)
                                            if b is not None:
                                                data_ref = b.get_editor_property("data_set_variable")
                                                if data_ref is not None:
                                                    bname = str(data_ref.get_editor_property("name"))
                                                    if bname:
                                                        bindings.append({{"name": prop_name, "bound_to": bname}})
                                        except Exception:
                                            pass
                                    if bindings:
                                        r_info["bindings"] = bindings
                                except Exception:
                                    pass
                                renderers_out.append(r_info)
                    except Exception:
                        pass
            result["emitters"].append({{"name": name, "renderers": renderers_out}})
    print(json.dumps(result))
'''


@mcp.tool()
def get_niagara_renderers(asset_path: str, emitter_name: str = "") -> str:
    """Get renderer details for emitters in a Niagara system.

    Lists each renderer's class, enabled state, sort order, material,
    and attribute bindings.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Optional emitter name to filter (empty = all emitters)
    """
    bridge = _get_bridge()
    escaped_path = _escape_py_string(asset_path)
    escaped_emitter = _escape_py_string(emitter_name or "")
    command = _RENDERERS_SCRIPT.format(
        asset_path=escaped_path, emitter_name=escaped_emitter
    )

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
        return f"No emitters found in {data.get('asset_path', '')}."

    lines = [f"Niagara Renderers: {data.get('asset_path', '')}", ""]
    for em in emitters:
        renderers = em.get("renderers", [])
        lines.append(f"Emitter: {em.get('name', '?')} ({len(renderers)} renderer(s))")
        if not renderers:
            lines.append("  (no renderers)")
        for r in renderers:
            enabled = "Enabled" if r.get("is_enabled", True) else "Disabled"
            lines.append(f"  [{r.get('index', '?')}] {r.get('class', '?')} ({enabled})")
            if "sort_order_hint" in r:
                lines.append(f"      Sort Order: {r['sort_order_hint']}")
            if "material" in r:
                mat = r["material"] or "(none)"
                lines.append(f"      Material: {mat}")
            bindings = r.get("bindings", [])
            if bindings:
                lines.append("      Bindings:")
                for b in bindings:
                    lines.append(f"        {b['name']} -> {b['bound_to']}")
        lines.append("")

    return "\n".join(lines).rstrip()
