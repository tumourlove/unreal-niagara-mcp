"""Niagara emitter and renderer editing tools using C++ plugin calls."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _call_plugin, _format_error


# ---------------------------------------------------------------------------
# add_emitter
# ---------------------------------------------------------------------------


@mcp.tool()
def add_emitter(
    asset_path: str,
    emitter_asset_path: str,
    name: str = "",
) -> str:
    """Add an emitter to a Niagara system from an emitter asset.

    asset_path: Full Unreal asset path of the system, e.g. '/Game/VFX/NS_Fire'
    emitter_asset_path: Asset path of the emitter to add, e.g. '/Niagara/DefaultEmitter'
    name: Optional custom name for the emitter handle
    """
    try:
        data = _call_plugin(
            "NiagaraMCPSystemLibrary",
            "AddEmitter",
            SystemPath=asset_path,
            EmitterAssetPath=emitter_asset_path,
            Name=name,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Added emitter:\n"
        f"  System: {asset_path}\n"
        f"  Source: {emitter_asset_path}\n"
        f"  Name: {data.get('name', name or '(auto)')}\n"
        f"  Handle ID: {data.get('handle_id', 'N/A')}"
    )


# ---------------------------------------------------------------------------
# remove_emitter
# ---------------------------------------------------------------------------


@mcp.tool()
def remove_emitter(asset_path: str, emitter_name_or_id: str) -> str:
    """Remove an emitter from a Niagara system.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name_or_id: Emitter name or handle ID to remove
    """
    try:
        data = _call_plugin(
            "NiagaraMCPSystemLibrary",
            "RemoveEmitter",
            SystemPath=asset_path,
            EmitterNameOrId=emitter_name_or_id,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Removed emitter:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name_or_id}\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# set_emitter_enabled
# ---------------------------------------------------------------------------


@mcp.tool()
def set_emitter_enabled(
    asset_path: str,
    emitter_name: str,
    enabled: bool,
) -> str:
    """Enable or disable an emitter in a Niagara system.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Name of the emitter
    enabled: True to enable, False to disable
    """
    try:
        data = _call_plugin(
            "NiagaraMCPSystemLibrary",
            "SetEmitterEnabled",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            Enabled=str(enabled).lower(),
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    state = "enabled" if enabled else "disabled"
    return (
        f"Emitter {state}:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# reorder_emitters
# ---------------------------------------------------------------------------


@mcp.tool()
def reorder_emitters(
    asset_path: str,
    emitter_order: list[str],
) -> str:
    """Reorder emitters in a Niagara system.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_order: List of emitter names in desired order
    """
    import json

    try:
        data = _call_plugin(
            "NiagaraMCPSystemLibrary",
            "ReorderEmitters",
            SystemPath=asset_path,
            EmitterOrder=json.dumps(emitter_order),
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Reordered emitters:\n"
        f"  System: {asset_path}\n"
        f"  New Order: {', '.join(emitter_order)}\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# set_emitter_property
# ---------------------------------------------------------------------------


@mcp.tool()
def set_emitter_property(
    asset_path: str,
    emitter_name: str,
    property_name: str,
    value: str,
) -> str:
    """Set a property on an emitter in a Niagara system.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Name of the emitter
    property_name: Property name (e.g. 'sim_target', 'local_space', 'calculation_bounds_mode')
    value: New value as string (parsed by the plugin)
    """
    try:
        data = _call_plugin(
            "NiagaraMCPSystemLibrary",
            "SetEmitterProperty",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            PropertyName=property_name,
            Value=value,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Set emitter property:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  Property: {property_name}\n"
        f"  Value: {value}\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# add_renderer
# ---------------------------------------------------------------------------


@mcp.tool()
def add_renderer(
    asset_path: str,
    emitter_name: str,
    renderer_class: str,
) -> str:
    """Add a renderer to an emitter in a Niagara system.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Name of the emitter
    renderer_class: Renderer class name (e.g. 'NiagaraSpriteRendererProperties',
                    'NiagaraMeshRendererProperties', 'NiagaraRibbonRendererProperties')
    """
    try:
        data = _call_plugin(
            "NiagaraMCPRendererLibrary",
            "AddRenderer",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            RendererClass=renderer_class,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Added renderer:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  Class: {renderer_class}\n"
        f"  Index: {data.get('index', 'N/A')}"
    )


# ---------------------------------------------------------------------------
# remove_renderer
# ---------------------------------------------------------------------------


@mcp.tool()
def remove_renderer(
    asset_path: str,
    emitter_name: str,
    renderer_index: int,
) -> str:
    """Remove a renderer from an emitter by index.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Name of the emitter
    renderer_index: Index of the renderer to remove (from get_niagara_renderers)
    """
    try:
        data = _call_plugin(
            "NiagaraMCPRendererLibrary",
            "RemoveRenderer",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            RendererIndex=str(renderer_index),
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Removed renderer:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  Index: {renderer_index}\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# set_renderer_material
# ---------------------------------------------------------------------------


@mcp.tool()
def set_renderer_material(
    asset_path: str,
    emitter_name: str,
    renderer_index: int,
    material_path: str,
) -> str:
    """Set the material on a renderer.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Name of the emitter
    renderer_index: Index of the renderer
    material_path: Asset path of the material to assign
    """
    try:
        data = _call_plugin(
            "NiagaraMCPRendererLibrary",
            "SetRendererMaterial",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            RendererIndex=str(renderer_index),
            MaterialPath=material_path,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Set renderer material:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  Renderer Index: {renderer_index}\n"
        f"  Material: {material_path}\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# set_renderer_property
# ---------------------------------------------------------------------------


@mcp.tool()
def set_renderer_property(
    asset_path: str,
    emitter_name: str,
    renderer_index: int,
    property_name: str,
    value: str,
) -> str:
    """Set a property on a renderer.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Name of the emitter
    renderer_index: Index of the renderer
    property_name: Property name to set (e.g. 'sort_order_hint', 'is_enabled')
    value: New value as string (parsed by the plugin)
    """
    try:
        data = _call_plugin(
            "NiagaraMCPRendererLibrary",
            "SetRendererProperty",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            RendererIndex=str(renderer_index),
            PropertyName=property_name,
            Value=value,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Set renderer property:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  Renderer Index: {renderer_index}\n"
        f"  Property: {property_name}\n"
        f"  Value: {value}\n"
        f"  Status: {data.get('status', 'OK')}"
    )
