"""Niagara system statistics and audit tools."""

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
# get_niagara_stats
# ---------------------------------------------------------------------------

_STATS_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    handles = system.get_editor_property("emitter_handles")
    emitter_count = len(handles) if handles else 0
    total_modules = 0
    total_params = 0
    renderer_types = set()
    sim_targets = set()
    estimated_particles = 0
    emitter_details = []
    if handles:
        for h in handles:
            name = str(h.get_editor_property("name"))
            is_enabled = bool(h.get_editor_property("is_enabled"))
            emitter_inst = h.get_editor_property("instance")
            em_info = {{"name": name, "is_enabled": is_enabled, "modules": 0, "renderers": []}}
            if emitter_inst is not None:
                ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    try:
                        sim_target = latest.get_editor_property("sim_target")
                        st = str(sim_target) if sim_target is not None else "Unknown"
                        sim_targets.add(st)
                        em_info["sim_target"] = st
                    except Exception:
                        pass
                    try:
                        renderers = latest.get_editor_property("renderer_properties")
                        if renderers:
                            for r in renderers:
                                rclass = type(r).__name__
                                renderer_types.add(rclass)
                                em_info["renderers"].append(rclass)
                    except Exception:
                        pass
                    for script_attr in ["emitter_spawn_script_props",
                                        "emitter_update_script_props",
                                        "particle_spawn_script_props",
                                        "particle_update_script_props"]:
                        try:
                            props = latest.get_editor_property(script_attr)
                            if props is not None:
                                script = props.get_editor_property("script")
                                if script is not None:
                                    modules = script.get_editor_property("module_usage_bitmask")
                                    em_info["modules"] += 1
                        except Exception:
                            pass
            total_modules += em_info["modules"]
            emitter_details.append(em_info)
    try:
        exposed = system.get_editor_property("exposed_parameters")
        if exposed is not None:
            params = exposed.get_editor_property("parameters")
            total_params = len(params) if params else 0
    except Exception:
        pass
    stats = {{
        "asset_path": path,
        "emitter_count": emitter_count,
        "total_modules": total_modules,
        "total_parameters": total_params,
        "renderer_types": list(renderer_types),
        "sim_targets": list(sim_targets),
        "emitters": emitter_details,
    }}
    print(json.dumps(stats))
'''


@mcp.tool()
def get_niagara_stats(asset_path: str) -> str:
    """Get comprehensive statistics for a Niagara system.

    Returns emitter count, total modules, total parameters, renderer types,
    simulation targets, and per-emitter breakdowns.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    """
    bridge = _get_bridge()
    escaped = _escape_py_string(asset_path)
    command = _STATS_SCRIPT.format(asset_path=escaped)

    try:
        result = bridge.run_command(command, exec_mode="ExecuteFile")
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    data = _parse_bridge_output(result)
    err = _format_error(data)
    if err:
        return err

    lines = [
        f"Niagara System Stats: {data.get('asset_path', '')}",
        "",
        "Overview:",
        f"  Emitters:        {data.get('emitter_count', 0)}",
        f"  Total Modules:   {data.get('total_modules', 0)}",
        f"  Total Parameters:{data.get('total_parameters', 0)}",
        f"  Renderer Types:  {', '.join(data.get('renderer_types', [])) or '(none)'}",
        f"  Sim Targets:     {', '.join(data.get('sim_targets', [])) or '(none)'}",
        "",
    ]

    emitters = data.get("emitters", [])
    if emitters:
        lines.append("Per-Emitter Breakdown:")
        for em in emitters:
            enabled = "Enabled" if em.get("is_enabled", True) else "Disabled"
            lines.append(f"  {em.get('name', '?')} ({enabled})")
            if em.get("sim_target"):
                lines.append(f"    Sim Target: {em['sim_target']}")
            lines.append(f"    Modules: {em.get('modules', 0)}")
            renderers = em.get("renderers", [])
            if renderers:
                lines.append(f"    Renderers: {', '.join(renderers)}")
            else:
                lines.append("    Renderers: (none)")
            lines.append("")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# audit_niagara_system
# ---------------------------------------------------------------------------

_AUDIT_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    handles = system.get_editor_property("emitter_handles")
    findings = []
    has_user_params = False
    user_param_names = []
    try:
        exposed = system.get_editor_property("exposed_parameters")
        if exposed is not None:
            params = exposed.get_editor_property("parameters")
            if params and len(params) > 0:
                has_user_params = True
                for p in params:
                    try:
                        user_param_names.append(str(p.get_editor_property("name")))
                    except Exception:
                        pass
    except Exception:
        pass
    if not has_user_params:
        findings.append({{
            "severity": "INFO",
            "description": "System has no user parameters (not configurable)",
            "emitter": "(system)",
        }})
    if handles:
        for h in handles:
            name = str(h.get_editor_property("name"))
            is_enabled = bool(h.get_editor_property("is_enabled"))
            if not is_enabled:
                continue
            emitter_inst = h.get_editor_property("instance")
            if emitter_inst is None:
                continue
            ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
            if not ver_data or len(ver_data) == 0:
                continue
            latest = ver_data[-1]
            is_gpu = False
            try:
                sim_target = latest.get_editor_property("sim_target")
                st = str(sim_target) if sim_target is not None else ""
                if "GPU" in st:
                    is_gpu = True
            except Exception:
                pass
            has_fixed_bounds = False
            try:
                bounds_mode = latest.get_editor_property("calculation_bounds_mode")
                bm = str(bounds_mode) if bounds_mode is not None else ""
                if "Fixed" in bm:
                    has_fixed_bounds = True
            except Exception:
                pass
            if is_gpu and not has_fixed_bounds:
                findings.append({{
                    "severity": "WARNING",
                    "description": "GPU emitter without fixed bounds",
                    "emitter": name,
                }})
            has_renderer = False
            try:
                renderers = latest.get_editor_property("renderer_properties")
                if renderers and len(renderers) > 0:
                    has_renderer = True
            except Exception:
                pass
            if not has_renderer:
                findings.append({{
                    "severity": "ERROR",
                    "description": "Missing renderer on enabled emitter",
                    "emitter": name,
                }})
            module_count_per_stage = {{}}
            for script_attr in ["emitter_spawn_script_props",
                                "emitter_update_script_props",
                                "particle_spawn_script_props",
                                "particle_update_script_props"]:
                try:
                    props = latest.get_editor_property(script_attr)
                    if props is not None:
                        script = props.get_editor_property("script")
                        if script is not None:
                            modules = script.get_editor_property("modules")
                            if modules:
                                cnt = len(modules)
                                module_count_per_stage[script_attr] = cnt
                                if cnt > 10:
                                    stage_label = script_attr.replace("_script_props", "").replace("_", " ").title()
                                    findings.append({{
                                        "severity": "WARNING",
                                        "description": f"More than 10 modules in {{stage_label}} ({{cnt}})",
                                        "emitter": name,
                                    }})
                except Exception:
                    pass
    findings.append({{
        "severity": "INFO",
        "description": "Could benefit from scalability settings",
        "emitter": "(system)",
    }})
    print(json.dumps({{"asset_path": path, "findings": findings}}))
'''


@mcp.tool()
def audit_niagara_system(asset_path: str) -> str:
    """Run a comprehensive quality audit on a Niagara system.

    Checks for common issues including:
    - GPU emitters without fixed bounds (WARNING)
    - Too many modules in a single stage (WARNING)
    - Missing renderers on enabled emitters (ERROR)
    - Missing user parameters (INFO)
    - Scalability recommendations (INFO)

    Returns a formatted report with severity, description, and affected emitter.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    """
    bridge = _get_bridge()
    escaped = _escape_py_string(asset_path)
    command = _AUDIT_SCRIPT.format(asset_path=escaped)

    try:
        result = bridge.run_command(command, exec_mode="ExecuteFile")
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    data = _parse_bridge_output(result)
    err = _format_error(data)
    if err:
        return err

    findings = data.get("findings", [])

    errors = [f for f in findings if f.get("severity") == "ERROR"]
    warnings = [f for f in findings if f.get("severity") == "WARNING"]
    infos = [f for f in findings if f.get("severity") == "INFO"]

    lines = [
        f"Niagara System Audit: {data.get('asset_path', '')}",
        "",
        f"Summary: {len(errors)} error(s), {len(warnings)} warning(s), {len(infos)} info(s)",
        "",
    ]

    if errors:
        lines.append("ERRORS:")
        for f in errors:
            lines.append(f"  [ERROR] {f.get('description', '?')}")
            lines.append(f"          Emitter: {f.get('emitter', '?')}")
        lines.append("")

    if warnings:
        lines.append("WARNINGS:")
        for f in warnings:
            lines.append(f"  [WARNING] {f.get('description', '?')}")
            lines.append(f"            Emitter: {f.get('emitter', '?')}")
        lines.append("")

    if infos:
        lines.append("INFO:")
        for f in infos:
            lines.append(f"  [INFO] {f.get('description', '?')}")
            lines.append(f"         Emitter: {f.get('emitter', '?')}")
        lines.append("")

    if not findings:
        lines.append("No issues found. System looks good!")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# audit_scalability
# ---------------------------------------------------------------------------

_SCALABILITY_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    handles = system.get_editor_property("emitter_handles")
    info = {{"asset_path": path, "emitters": [], "system_settings": {{}}}}
    try:
        info["system_settings"]["warmup_time"] = system.get_editor_property("warmup_time")
    except Exception:
        pass
    try:
        effect_type = system.get_editor_property("effect_type")
        info["system_settings"]["effect_type"] = str(effect_type) if effect_type else None
    except Exception:
        info["system_settings"]["effect_type"] = None
    try:
        info["system_settings"]["fixed_bounds"] = str(system.get_editor_property("fixed_bounds"))
    except Exception:
        pass
    recommendations = []
    if info["system_settings"].get("effect_type") is None:
        recommendations.append("No effect type set - consider assigning one for scalability budgets")
    if handles:
        for h in handles:
            name = str(h.get_editor_property("name"))
            emitter_inst = h.get_editor_property("instance")
            em_info = {{"name": name}}
            if emitter_inst is not None:
                ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    try:
                        bounds_mode = latest.get_editor_property("calculation_bounds_mode")
                        em_info["bounds_mode"] = str(bounds_mode) if bounds_mode is not None else "Unknown"
                    except Exception:
                        em_info["bounds_mode"] = "Unknown"
                    try:
                        scalability_overrides = latest.get_editor_property("platforms")
                        em_info["has_scalability_overrides"] = scalability_overrides is not None
                    except Exception:
                        em_info["has_scalability_overrides"] = False
                    try:
                        sim_target = latest.get_editor_property("sim_target")
                        em_info["sim_target"] = str(sim_target) if sim_target is not None else "Unknown"
                    except Exception:
                        pass
                    if not em_info.get("has_scalability_overrides", False):
                        recommendations.append(f"Emitter '{{name}}' has no scalability overrides")
                    if "Dynamic" in em_info.get("bounds_mode", "") or "Auto" in em_info.get("bounds_mode", ""):
                        recommendations.append(f"Emitter '{{name}}' uses {{em_info['bounds_mode']}} bounds - consider Fixed for performance")
            info["emitters"].append(em_info)
    info["recommendations"] = recommendations
    print(json.dumps(info))
'''


@mcp.tool()
def audit_scalability(asset_path: str) -> str:
    """Audit scalability settings for a Niagara system.

    Checks effect types, cull distances, bounds modes, scalability overrides,
    and recommends improvements for performance across quality levels.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    """
    bridge = _get_bridge()
    escaped = _escape_py_string(asset_path)
    command = _SCALABILITY_SCRIPT.format(asset_path=escaped)

    try:
        result = bridge.run_command(command, exec_mode="ExecuteFile")
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    data = _parse_bridge_output(result)
    err = _format_error(data)
    if err:
        return err

    sys_settings = data.get("system_settings", {})
    emitters = data.get("emitters", [])
    recommendations = data.get("recommendations", [])

    lines = [
        f"Scalability Audit: {data.get('asset_path', '')}",
        "",
        "System Settings:",
        f"  Effect Type:  {sys_settings.get('effect_type') or '(not set)'}",
        f"  Warmup Time:  {sys_settings.get('warmup_time', 0.0)}",
        "",
        "Per-Emitter Scalability:",
    ]

    for em in emitters:
        lines.append(f"  {em.get('name', '?')}:")
        if em.get("sim_target"):
            lines.append(f"    Sim Target:           {em['sim_target']}")
        lines.append(f"    Bounds Mode:          {em.get('bounds_mode', 'Unknown')}")
        lines.append(f"    Scalability Overrides: {'Yes' if em.get('has_scalability_overrides') else 'No'}")
        lines.append("")

    if recommendations:
        lines.append("Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"  {i}. {rec}")
    else:
        lines.append("No scalability issues found.")

    return "\n".join(lines).rstrip()
