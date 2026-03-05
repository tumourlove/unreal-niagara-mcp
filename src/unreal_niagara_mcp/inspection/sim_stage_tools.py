"""Niagara simulation stage inspection tools using UPROPERTY reads."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _escape_py_string, _format_error


# ---------------------------------------------------------------------------
# get_simulation_stages
# ---------------------------------------------------------------------------

_SIM_STAGES_SCRIPT = '''\
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
            stages_out = []
            if emitter_inst is not None:
                ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    try:
                        sim_stages = latest.get_editor_property("simulation_stages")
                        if sim_stages:
                            for idx, ss in enumerate(sim_stages):
                                stage = {{"index": idx}}
                                try:
                                    stage["simulation_stage_name"] = str(ss.get_editor_property("simulation_stage_name"))
                                except Exception:
                                    pass
                                try:
                                    stage["iteration_source"] = str(ss.get_editor_property("iteration_source"))
                                except Exception:
                                    pass
                                try:
                                    stage["num_iterations"] = int(ss.get_editor_property("num_iterations"))
                                except Exception:
                                    pass
                                try:
                                    stage["execute_before"] = bool(ss.get_editor_property("execute_before"))
                                except Exception:
                                    pass
                                try:
                                    stage["enabled"] = bool(ss.get_editor_property("enabled"))
                                except Exception:
                                    stage["enabled"] = True
                                try:
                                    di = ss.get_editor_property("data_interface")
                                    if di is not None:
                                        stage["data_interface"] = type(di).__name__
                                except Exception:
                                    pass
                                stages_out.append(stage)
                    except Exception:
                        pass
            result["emitters"].append({{"name": name, "simulation_stages": stages_out}})
    print(json.dumps(result))
'''


@mcp.tool()
def get_simulation_stages(asset_path: str, emitter_name: str = "") -> str:
    """Get simulation stage configurations in a Niagara system.

    Shows each simulation stage's name, iteration source,
    iteration count, and data interface binding.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Optional emitter name filter (empty = all emitters)
    """
    bridge = _get_bridge()
    escaped_path = _escape_py_string(asset_path)
    escaped_emitter = _escape_py_string(emitter_name or "")
    command = _SIM_STAGES_SCRIPT.format(
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

    lines = [f"Simulation Stages: {asset_path}", ""]
    total = 0
    for em in emitters:
        stages = em.get("simulation_stages", [])
        total += len(stages)
        lines.append(f"Emitter: {em.get('name', '?')} ({len(stages)} simulation stage(s))")
        if not stages:
            lines.append("  (none)")
        for ss in stages:
            enabled = "Enabled" if ss.get("enabled", True) else "Disabled"
            lines.append(f"  [{ss.get('index', '?')}] {ss.get('simulation_stage_name', '?')} ({enabled})")
            if ss.get("iteration_source"):
                lines.append(f"      Iteration Source: {ss['iteration_source']}")
            if "num_iterations" in ss:
                lines.append(f"      Iterations: {ss['num_iterations']}")
            if "execute_before" in ss:
                lines.append(f"      Execute Before: {ss['execute_before']}")
            if ss.get("data_interface"):
                lines.append(f"      Data Interface: {ss['data_interface']}")
        lines.append("")

    if total == 0:
        return f"No simulation stages found in {asset_path}."

    return "\n".join(lines).rstrip()
