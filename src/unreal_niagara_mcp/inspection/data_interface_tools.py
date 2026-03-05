"""Niagara data interface inspection tools using UPROPERTY reads."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _escape_py_string, _format_error


# ---------------------------------------------------------------------------
# get_data_interfaces
# ---------------------------------------------------------------------------

_DI_SCRIPT = '''\
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
            dis_out = []
            if emitter_inst is not None:
                ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    try:
                        scripts = []
                        for script_attr in ["emitter_spawn_script_props",
                                            "emitter_update_script_props",
                                            "particle_spawn_script_props",
                                            "particle_update_script_props"]:
                            try:
                                props = latest.get_editor_property(script_attr)
                                if props is not None:
                                    try:
                                        script = props.get_editor_property("script")
                                        if script is not None:
                                            scripts.append((script_attr, script))
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        for script_attr, script in scripts:
                            try:
                                dis = script.get_editor_property("data_interface_info")
                                if dis:
                                    for di in dis:
                                        try:
                                            di_obj = di.get_editor_property("data_interface")
                                            if di_obj is not None:
                                                di_class = type(di_obj).__name__
                                                di_name_prop = ""
                                                try:
                                                    di_name_prop = str(di.get_editor_property("name"))
                                                except Exception:
                                                    pass
                                                dis_out.append({{
                                                    "class": di_class,
                                                    "name": di_name_prop,
                                                    "stage": script_attr.replace("_script_props", ""),
                                                }})
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                    except Exception:
                        pass
            result["emitters"].append({{"name": name, "data_interfaces": dis_out}})
    print(json.dumps(result))
'''


@mcp.tool()
def get_data_interfaces(asset_path: str, emitter_name: str = "") -> str:
    """Get data interface instances used in a Niagara system.

    Data interfaces provide external data to Niagara (skeletal mesh,
    audio, curves, etc.).

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Optional emitter name filter (empty = all emitters)
    """
    bridge = _get_bridge()
    escaped_path = _escape_py_string(asset_path)
    escaped_emitter = _escape_py_string(emitter_name or "")
    command = _DI_SCRIPT.format(
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
        return f"No emitters found in {asset_path}."

    lines = [f"Data Interfaces: {asset_path}", ""]
    total = 0
    for em in emitters:
        dis = em.get("data_interfaces", [])
        total += len(dis)
        lines.append(f"Emitter: {em.get('name', '?')} ({len(dis)} DI(s))")
        if not dis:
            lines.append("  (none)")
        for di in dis:
            lines.append(f"  {di.get('class', '?')}")
            if di.get("name"):
                lines.append(f"    Name: {di['name']}")
            if di.get("stage"):
                lines.append(f"    Stage: {di['stage']}")
        lines.append("")

    lines.insert(1, f"Total: {total} data interface(s)")
    lines.insert(2, "")

    return "\n".join(lines).rstrip()
