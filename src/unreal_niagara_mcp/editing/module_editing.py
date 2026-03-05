"""Niagara module editing tools using C++ plugin calls."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _call_plugin, _format_error


# ---------------------------------------------------------------------------
# add_module
# ---------------------------------------------------------------------------


@mcp.tool()
def add_module(
    asset_path: str,
    emitter_name: str,
    stage: str,
    module_script_path: str,
    index: int = -1,
) -> str:
    """Add a module to an emitter stage in a Niagara system.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: The emitter to add the module to
    stage: Stage name (ParticleSpawn, ParticleUpdate, EmitterSpawn, EmitterUpdate, etc.)
    module_script_path: Asset path of the module script to add
    index: Insert position (-1 = append at end)
    """
    try:
        data = _call_plugin(
            "NiagaraMCPModuleLibrary",
            "AddModule",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            Stage=stage,
            ModuleScriptPath=module_script_path,
            Index=str(index),
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Added module:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  Stage: {stage}\n"
        f"  Module: {module_script_path}\n"
        f"  Index: {data.get('index', index)}\n"
        f"  GUID: {data.get('guid', 'N/A')}"
    )


# ---------------------------------------------------------------------------
# remove_module
# ---------------------------------------------------------------------------


@mcp.tool()
def remove_module(
    asset_path: str,
    emitter_name: str,
    module_guid: str,
) -> str:
    """Remove a module from a Niagara emitter by its GUID.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: The emitter containing the module
    module_guid: The GUID of the module to remove (from get_niagara_modules)
    """
    try:
        data = _call_plugin(
            "NiagaraMCPModuleLibrary",
            "RemoveModule",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            ModuleGuid=module_guid,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Removed module:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  GUID: {module_guid}\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# reorder_modules
# ---------------------------------------------------------------------------


@mcp.tool()
def reorder_modules(
    asset_path: str,
    emitter_name: str,
    stage: str,
    module_guids: list[str],
) -> str:
    """Reorder modules within an emitter stage by specifying the desired GUID order.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: The emitter to reorder modules in
    stage: Stage name (ParticleSpawn, ParticleUpdate, etc.)
    module_guids: Ordered list of module GUIDs in desired order
    """
    import json

    try:
        data = _call_plugin(
            "NiagaraMCPModuleLibrary",
            "MoveModule",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            Stage=stage,
            ModuleGuids=json.dumps(module_guids),
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Reordered modules:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  Stage: {stage}\n"
        f"  New Order: {len(module_guids)} module(s)\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# set_module_enabled
# ---------------------------------------------------------------------------


@mcp.tool()
def set_module_enabled(
    asset_path: str,
    emitter_name: str,
    module_guid: str,
    enabled: bool,
) -> str:
    """Enable or disable a module in a Niagara emitter.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: The emitter containing the module
    module_guid: The GUID of the module
    enabled: True to enable, False to disable
    """
    try:
        data = _call_plugin(
            "NiagaraMCPModuleLibrary",
            "SetModuleEnabled",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            ModuleGuid=module_guid,
            Enabled=str(enabled).lower(),
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    state = "enabled" if enabled else "disabled"
    return (
        f"Module {state}:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  GUID: {module_guid}\n"
        f"  Status: {data.get('status', 'OK')}"
    )
