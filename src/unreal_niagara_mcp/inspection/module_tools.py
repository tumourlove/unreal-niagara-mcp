"""Niagara module inspection tools using C++ plugin calls."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _call_plugin, _escape_py_string, _format_error


# ---------------------------------------------------------------------------
# Stage ordering for display
# ---------------------------------------------------------------------------

_STAGES = [
    "SystemSpawn",
    "SystemUpdate",
    "EmitterSpawn",
    "EmitterUpdate",
    "ParticleSpawn",
    "ParticleUpdate",
    "Event",
    "SimulationStage",
]


# ---------------------------------------------------------------------------
# get_niagara_modules
# ---------------------------------------------------------------------------


@mcp.tool()
def get_niagara_modules(
    asset_path: str,
    emitter_name: str = "",
    stage: str = "",
) -> str:
    """List all modules in a Niagara system, organized by emitter and stage.

    Calls the C++ plugin GetOrderedModules for each applicable stage,
    presenting results as a tree.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Optional emitter name filter (empty = all emitters)
    stage: Optional stage filter (e.g. 'ParticleUpdate'). Empty = all stages.
    """
    stages_to_query = [stage] if stage else _STAGES

    try:
        data = _call_plugin(
            "NiagaraMCPModuleLibrary",
            "GetOrderedModules",
            SystemPath=asset_path,
            EmitterName=emitter_name or "",
            Stage=",".join(stages_to_query),
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    emitters = data.get("emitters", [])
    if not emitters and not data.get("system_modules"):
        return f"No modules found in {asset_path}."

    lines = [f"Niagara Modules: {asset_path}", ""]

    # System-level modules
    sys_modules = data.get("system_modules", {})
    if sys_modules:
        lines.append("System:")
        for stage_name, mods in sys_modules.items():
            if mods:
                lines.append(f"  {stage_name}:")
                for m in mods:
                    enabled = "" if m.get("is_enabled", True) else " [DISABLED]"
                    lines.append(f"    [{m.get('index', '?')}] {m.get('name', '?')}{enabled}")
                    if m.get("guid"):
                        lines.append(f"         GUID: {m['guid']}")
        lines.append("")

    # Per-emitter modules
    for em in emitters:
        lines.append(f"Emitter: {em.get('name', '?')}")
        stages = em.get("stages", {})
        if not stages:
            lines.append("  (no modules)")
        for stage_name in _STAGES:
            mods = stages.get(stage_name, [])
            if mods:
                lines.append(f"  {stage_name}:")
                for m in mods:
                    enabled = "" if m.get("is_enabled", True) else " [DISABLED]"
                    lines.append(f"    [{m.get('index', '?')}] {m.get('name', '?')}{enabled}")
                    if m.get("guid"):
                        lines.append(f"         GUID: {m['guid']}")
                    if m.get("script_path"):
                        lines.append(f"         Script: {m['script_path']}")
        lines.append("")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# get_module_inputs
# ---------------------------------------------------------------------------


@mcp.tool()
def get_module_inputs(
    asset_path: str,
    emitter_name: str,
    module_name: str,
) -> str:
    """Get all input parameters for a specific module.

    Returns each input's name, type, current value, and default value.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: The emitter containing the module
    module_name: Name of the module to inspect
    """
    try:
        data = _call_plugin(
            "NiagaraMCPModuleLibrary",
            "GetModuleInputs",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            ModuleName=module_name,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    inputs = data.get("inputs", [])
    if not inputs:
        return f"No inputs found for module '{module_name}' in emitter '{emitter_name}'."

    lines = [
        f"Module Inputs: {module_name}",
        f"  Emitter: {emitter_name}",
        f"  System: {asset_path}",
        "",
        f"  {'Name':<35} {'Type':<20} {'Value':<25} {'Default':<25}",
        f"  {'-'*35} {'-'*20} {'-'*25} {'-'*25}",
    ]
    for inp in inputs:
        name = inp.get("name", "?")
        type_name = inp.get("type", "?")
        value = str(inp.get("value", ""))
        default = str(inp.get("default", ""))
        lines.append(f"  {name:<35} {type_name:<20} {value:<25} {default:<25}")

    return "\n".join(lines)
