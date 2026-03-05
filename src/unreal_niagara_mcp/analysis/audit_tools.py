"""Niagara pooling and binding audit tools."""

from __future__ import annotations

import json

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
# audit_pooling
# ---------------------------------------------------------------------------

_POOLING_SCRIPT = '''\
import unreal, json
path = "__ASSET_PATH__"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": "Cannot load asset: " + path}}))
else:
    info = {{"asset_path": path}}
    pool_prime_size = 0
    pool_method = "None"
    try:
        pool_prime_size = system.get_editor_property("pool_prime_size")
    except Exception:
        pass
    try:
        pm = system.get_editor_property("pool_method")
        pool_method = str(pm) if pm is not None else "None"
    except Exception:
        pass
    try:
        auto_deactivate = system.get_editor_property("auto_deactivate")
        info["auto_deactivate"] = bool(auto_deactivate)
    except Exception:
        info["auto_deactivate"] = False
    info["pool_prime_size"] = pool_prime_size
    info["pool_method"] = pool_method
    handles = system.get_editor_property("emitter_handles")
    emitter_count = len(handles) if handles else 0
    info["emitter_count"] = emitter_count
    has_burst = False
    has_continuous = False
    if handles:
        for h in handles:
            is_enabled = bool(h.get_editor_property("is_enabled"))
            if not is_enabled:
                continue
            emitter_inst = h.get_editor_property("instance")
            if emitter_inst is not None:
                ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    try:
                        props = latest.get_editor_property("particle_spawn_script_props")
                        if props is not None:
                            script = props.get_editor_property("script")
                            if script is not None:
                                modules = script.get_editor_property("modules")
                                if modules:
                                    for m in modules:
                                        mname = str(type(m).__name__).lower()
                                        if "burst" in mname:
                                            has_burst = True
                                        if "spawnrate" in mname or "spawn_rate" in mname:
                                            has_continuous = True
                    except Exception:
                        pass
    info["has_burst_spawn"] = has_burst
    info["has_continuous_spawn"] = has_continuous
    recommendations = []
    uses_pooling = pool_method != "None" and pool_method != "ENiagaraPoolingMethod.NONE"
    info["uses_pooling"] = uses_pooling
    if not uses_pooling:
        if has_burst and not has_continuous:
            recommendations.append("System uses burst spawning - good candidate for pooling")
            recommendations.append("Recommended pool size: 4-8 instances")
        elif has_continuous:
            recommendations.append("System uses continuous spawning - may benefit from pooling if spawned frequently")
            recommendations.append("Recommended pool size: 2-4 instances")
        else:
            recommendations.append("Consider enabling pooling if this system is spawned at runtime")
    else:
        if pool_prime_size == 0:
            recommendations.append("Pooling is enabled (" + pool_method + ") but pool_prime_size is 0 - consider priming")
        if not info.get("auto_deactivate", False):
            recommendations.append("Pool method set but auto_deactivate is off - pooling may not reclaim instances")
    info["recommendations"] = recommendations
    print(json.dumps(info))
'''


@mcp.tool()
def audit_pooling(asset_path: str) -> str:
    """Audit pooling settings for a Niagara system.

    Checks if the system uses component pooling, analyzes spawn patterns
    (burst vs continuous), and recommends pool sizes.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    """
    bridge = _get_bridge()
    escaped = _escape_py_string(asset_path)
    command = _POOLING_SCRIPT.replace("__ASSET_PATH__", escaped)

    try:
        result = bridge.run_command(command, exec_mode="ExecuteFile")
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    data = _parse_bridge_output(result)
    err = _format_error(data)
    if err:
        return err

    uses_pooling = data.get("uses_pooling", False)
    recommendations = data.get("recommendations", [])

    lines = [
        f"Pooling Audit: {data.get('asset_path', '')}",
        "",
        "Current Settings:",
        f"  Pool Method:     {data.get('pool_method', 'None')}",
        f"  Pool Prime Size: {data.get('pool_prime_size', 0)}",
        f"  Auto Deactivate: {data.get('auto_deactivate', False)}",
        f"  Uses Pooling:    {'Yes' if uses_pooling else 'No'}",
        "",
        "Spawn Analysis:",
        f"  Emitter Count:       {data.get('emitter_count', 0)}",
        f"  Has Burst Spawn:     {'Yes' if data.get('has_burst_spawn') else 'No'}",
        f"  Has Continuous Spawn:{'Yes' if data.get('has_continuous_spawn') else 'No'}",
        "",
    ]

    if recommendations:
        lines.append("Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"  {i}. {rec}")
    else:
        lines.append("Pooling configuration looks good.")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# validate_bindings
# ---------------------------------------------------------------------------


@mcp.tool()
def validate_bindings(asset_path: str, emitter_name: str = "") -> str:
    """Validate all module input bindings in a Niagara system.

    Checks that parameter bindings are valid and reports any broken or
    missing bindings. Uses C++ TraceParameterBinding for user parameters
    and inspects module inputs for correctness.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Optional emitter name filter (empty = all emitters)
    """
    try:
        data = _call_plugin(
            "NiagaraMCPAnalysisLibrary",
            "ValidateBindings",
            SystemPath=asset_path,
            EmitterName=emitter_name or "",
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    emitters = data.get("emitters", [])
    total_checked = data.get("total_checked", 0)
    total_broken = data.get("total_broken", 0)
    total_warnings = data.get("total_warnings", 0)

    lines = [
        f"Binding Validation: {asset_path}",
        "",
        f"Summary: {total_checked} binding(s) checked, "
        f"{total_broken} broken, {total_warnings} warning(s)",
        "",
    ]

    if not emitters:
        lines.append("No emitters to validate.")
        return "\n".join(lines)

    for em in emitters:
        bindings = em.get("bindings", [])
        broken = [b for b in bindings if b.get("status") == "broken"]
        warned = [b for b in bindings if b.get("status") == "warning"]
        valid = [b for b in bindings if b.get("status") == "valid"]

        status_str = "OK" if not broken and not warned else f"{len(broken)} broken, {len(warned)} warning(s)"
        lines.append(f"Emitter: {em.get('name', '?')} ({status_str})")

        if broken:
            for b in broken:
                lines.append(f"  [BROKEN] {b.get('module', '?')}.{b.get('input', '?')}")
                lines.append(f"           Bound to: {b.get('bound_to', '?')} (not found)")
                if b.get("suggestion"):
                    lines.append(f"           Suggestion: {b['suggestion']}")

        if warned:
            for b in warned:
                lines.append(f"  [WARNING] {b.get('module', '?')}.{b.get('input', '?')}")
                lines.append(f"            {b.get('message', '?')}")

        if not broken and not warned:
            lines.append(f"  All {len(valid)} binding(s) valid")

        lines.append("")

    return "\n".join(lines).rstrip()
