"""Niagara dream features: particle count preview, HLSL output, batch updates."""

from __future__ import annotations

import json
from typing import Any

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _call_plugin, _escape_py_string, _format_error


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
# preview_particle_count
# ---------------------------------------------------------------------------

_SPAWN_INFO_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
emitter_filter = "{emitter_name}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    handles = system.get_editor_property("emitter_handles")
    emitters_info = []
    if handles:
        for h in handles:
            name = str(h.get_editor_property("name"))
            if emitter_filter and name != emitter_filter:
                continue
            is_enabled = bool(h.get_editor_property("is_enabled"))
            if not is_enabled:
                continue
            em_info = {{"name": name, "spawn_rate": 0.0, "burst_count": 0, "lifetime": 1.0, "spawn_type": "unknown"}}
            emitter_inst = h.get_editor_property("instance")
            if emitter_inst is not None:
                ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    for script_attr in ["particle_spawn_script_props", "emitter_update_script_props"]:
                        try:
                            props = latest.get_editor_property(script_attr)
                            if props is not None:
                                script = props.get_editor_property("script")
                                if script is not None:
                                    modules = script.get_editor_property("modules")
                                    if modules:
                                        for m in modules:
                                            mname = type(m).__name__.lower()
                                            if "spawnrate" in mname or "spawn_rate" in mname:
                                                em_info["spawn_type"] = "continuous"
                                                try:
                                                    rate = m.get_editor_property("spawn_rate")
                                                    em_info["spawn_rate"] = float(rate)
                                                except Exception:
                                                    em_info["spawn_rate"] = 100.0
                                            elif "burst" in mname:
                                                em_info["spawn_type"] = "burst"
                                                try:
                                                    count = m.get_editor_property("spawn_count")
                                                    em_info["burst_count"] = int(count)
                                                except Exception:
                                                    em_info["burst_count"] = 10
                        except Exception:
                            pass
                    try:
                        props = latest.get_editor_property("particle_update_script_props")
                        if props is not None:
                            script = props.get_editor_property("script")
                            if script is not None:
                                modules = script.get_editor_property("modules")
                                if modules:
                                    for m in modules:
                                        mname = type(m).__name__.lower()
                                        if "lifetime" in mname:
                                            try:
                                                lt = m.get_editor_property("lifetime")
                                                em_info["lifetime"] = float(lt)
                                            except Exception:
                                                pass
                    except Exception:
                        pass
            emitters_info.append(em_info)
    print(json.dumps({{"asset_path": path, "emitters": emitters_info}}))
'''


def _compute_particle_table(
    spawn_type: str,
    spawn_rate: float,
    burst_count: int,
    lifetime: float,
    time_range: float,
) -> list[dict[str, float]]:
    """Compute estimated alive particle counts over time.

    For continuous spawning: alive = spawn_rate * min(elapsed, lifetime)
    For burst: alive = burst_count while elapsed < lifetime, then 0
    """
    steps = 10
    dt = time_range / steps
    table = []

    for i in range(steps + 1):
        t = round(i * dt, 3)
        if spawn_type == "continuous":
            alive = spawn_rate * min(t, lifetime)
        elif spawn_type == "burst":
            alive = float(burst_count) if t < lifetime else 0.0
        else:
            alive = 0.0
        table.append({"time": t, "alive": round(alive, 1)})

    return table


@mcp.tool()
def preview_particle_count(
    asset_path: str,
    emitter_name: str = "",
    time_range: float = 5.0,
) -> str:
    """Preview estimated particle counts over time for a Niagara system.

    Uses pure math based on spawn rate and lifetime to compute how many
    particles would be alive at each time step. Useful for performance
    estimation without needing to run the simulation.

    For continuous spawning: alive = spawn_rate * min(elapsed, lifetime)
    For burst: alive = burst_count while elapsed < lifetime, then 0

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Optional emitter name filter (empty = all emitters)
    time_range: Time range in seconds to preview (default: 5.0)
    """
    bridge = _get_bridge()
    escaped_path = _escape_py_string(asset_path)
    escaped_emitter = _escape_py_string(emitter_name or "")
    command = _SPAWN_INFO_SCRIPT.format(
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

    emitters = data.get("emitters", [])
    if not emitters:
        return f"No enabled emitters found in {asset_path}."

    lines = [
        f"Particle Count Preview: {data.get('asset_path', '')}",
        f"Time Range: 0 - {time_range}s",
        "",
    ]

    for em in emitters:
        name = em.get("name", "?")
        spawn_type = em.get("spawn_type", "unknown")
        spawn_rate = em.get("spawn_rate", 0.0)
        burst_count = em.get("burst_count", 0)
        lifetime = em.get("lifetime", 1.0)

        lines.append(f"Emitter: {name}")
        lines.append(f"  Spawn Type: {spawn_type}")
        if spawn_type == "continuous":
            lines.append(f"  Spawn Rate: {spawn_rate}/s")
        elif spawn_type == "burst":
            lines.append(f"  Burst Count: {burst_count}")
        lines.append(f"  Lifetime: {lifetime}s")
        lines.append("")

        table = _compute_particle_table(
            spawn_type, spawn_rate, burst_count, lifetime, time_range
        )

        lines.append(f"  {'Time (s)':<12} {'Est. Alive':<12}")
        lines.append(f"  {'-'*12} {'-'*12}")
        peak = 0.0
        for row in table:
            t = row["time"]
            alive = row["alive"]
            peak = max(peak, alive)
            lines.append(f"  {t:<12.3f} {alive:<12.1f}")

        lines.append("")
        lines.append(f"  Peak Particles: {peak:.0f}")
        lines.append("")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# get_hlsl_output
# ---------------------------------------------------------------------------


@mcp.tool()
def get_hlsl_output(asset_path: str, emitter_name: str) -> str:
    """Get the compiled GPU HLSL output for a Niagara emitter.

    Retrieves the generated HLSL shader code that the GPU simulation
    compiles to. Only works for GPU emitters.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Name of the GPU emitter to get HLSL for
    """
    try:
        data = _call_plugin(
            "NiagaraMCPAnalysisLibrary",
            "GetCompiledGPUHLSL",
            SystemPath=asset_path,
            EmitterName=emitter_name,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    hlsl = data.get("hlsl", "")
    emitter = data.get("emitter_name", emitter_name)
    compile_status = data.get("compile_status", "Unknown")

    lines = [
        f"Compiled GPU HLSL: {emitter}",
        f"System: {asset_path}",
        f"Compile Status: {compile_status}",
        "",
    ]

    if not hlsl:
        lines.append("(No HLSL output available - emitter may not be GPU or may not be compiled)")
        return "\n".join(lines)

    lines.append("--- HLSL BEGIN ---")
    for code_line in hlsl.split("\n"):
        lines.append(code_line)
    lines.append("--- HLSL END ---")

    # Stats
    line_count = len(hlsl.split("\n"))
    lines.append("")
    lines.append(f"Total Lines: {line_count}")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# batch_update_niagara
# ---------------------------------------------------------------------------


@mcp.tool()
def batch_update_niagara(updates: str) -> str:
    """Apply batch updates across multiple Niagara systems.

    Takes a JSON string describing updates to apply to one or more systems.
    Each entry specifies an asset path and a list of operations.

    Format:
    [
      {
        "asset_path": "/Game/VFX/NS_Fire",
        "operations": [
          {"op": "set_input", "emitter": "Flames", "module": "SpawnRate", "input": "SpawnRate", "value": "200"},
          {"op": "enable_emitter", "emitter": "Smoke", "enabled": true}
        ]
      }
    ]

    Supported operations:
    - set_input: Set a module input value
    - enable_emitter: Enable/disable an emitter
    - set_sim_target: Change simulation target
    - add_module: Add a module to an emitter stage

    updates: JSON string with the update specifications
    """
    try:
        update_list = json.loads(updates)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in updates parameter: {e}"

    if not isinstance(update_list, list):
        return "Error: updates must be a JSON array of objects"

    results = []
    total_ops = 0
    total_success = 0
    total_failed = 0

    for entry in update_list:
        asset_path = entry.get("asset_path", "")
        operations = entry.get("operations", [])

        if not asset_path:
            results.append({"asset_path": "(missing)", "status": "error", "message": "No asset_path specified"})
            total_failed += len(operations) if operations else 1
            continue

        for op in operations:
            total_ops += 1
            op_type = op.get("op", "unknown")

            try:
                if op_type == "set_input":
                    data = _call_plugin(
                        "NiagaraMCPEditLibrary",
                        "SetModuleInput",
                        SystemPath=asset_path,
                        EmitterName=op.get("emitter", ""),
                        ModuleName=op.get("module", ""),
                        InputName=op.get("input", ""),
                        Value=str(op.get("value", "")),
                    )
                elif op_type == "enable_emitter":
                    enabled_str = "true" if op.get("enabled", True) else "false"
                    data = _call_plugin(
                        "NiagaraMCPEditLibrary",
                        "SetEmitterEnabled",
                        SystemPath=asset_path,
                        EmitterName=op.get("emitter", ""),
                        Enabled=enabled_str,
                    )
                elif op_type == "set_sim_target":
                    data = _call_plugin(
                        "NiagaraMCPEditLibrary",
                        "SetSimTarget",
                        SystemPath=asset_path,
                        EmitterName=op.get("emitter", ""),
                        SimTarget=op.get("sim_target", "CPUSim"),
                    )
                elif op_type == "add_module":
                    data = _call_plugin(
                        "NiagaraMCPEditLibrary",
                        "AddModule",
                        SystemPath=asset_path,
                        EmitterName=op.get("emitter", ""),
                        ModulePath=op.get("module_path", ""),
                        Stage=op.get("stage", "ParticleUpdate"),
                    )
                else:
                    data = {"error": True, "message": f"Unknown operation: {op_type}"}

                if data.get("error"):
                    total_failed += 1
                    results.append({
                        "asset_path": asset_path,
                        "op": op_type,
                        "status": "failed",
                        "message": data.get("message", "Unknown error"),
                    })
                else:
                    total_success += 1
                    results.append({
                        "asset_path": asset_path,
                        "op": op_type,
                        "status": "success",
                    })

            except EditorNotRunning as e:
                total_failed += 1
                results.append({
                    "asset_path": asset_path,
                    "op": op_type,
                    "status": "failed",
                    "message": f"Editor not available: {e}",
                })

    lines = [
        "Batch Update Results",
        "",
        f"Total Operations: {total_ops}",
        f"Successful: {total_success}",
        f"Failed: {total_failed}",
        "",
    ]

    if results:
        lines.append("Details:")
        for r in results:
            status = r.get("status", "?")
            icon = "OK" if status == "success" else "FAIL"
            lines.append(f"  [{icon}] {r.get('asset_path', '?')} - {r.get('op', '?')}")
            if r.get("message"):
                lines.append(f"         {r['message']}")

    return "\n".join(lines).rstrip()
