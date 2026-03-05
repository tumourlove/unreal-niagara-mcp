"""Niagara parameter inspection tools using C++ plugin calls."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _call_plugin, _format_error


# ---------------------------------------------------------------------------
# get_niagara_parameters
# ---------------------------------------------------------------------------


@mcp.tool()
def get_niagara_parameters(asset_path: str) -> str:
    """Get all parameters in a Niagara system, grouped by namespace.

    Returns system, emitter, particle, user, engine, and other
    parameter namespaces with types and current values.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    """
    try:
        data = _call_plugin(
            "NiagaraMCPParameterLibrary",
            "GetAllParameters",
            SystemPath=asset_path,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    namespaces = data.get("namespaces", {})
    if not namespaces:
        return f"No parameters found in {asset_path}."

    lines = [f"Niagara Parameters: {asset_path}", ""]

    for ns_name, params in sorted(namespaces.items()):
        lines.append(f"{ns_name} ({len(params)} parameter(s)):")
        for p in params:
            name = p.get("name", "?")
            type_name = p.get("type", "?")
            value = p.get("value", "")
            value_str = f" = {value}" if value != "" else ""
            lines.append(f"  {name} ({type_name}){value_str}")
        lines.append("")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# get_niagara_user_parameters
# ---------------------------------------------------------------------------


@mcp.tool()
def get_niagara_user_parameters(asset_path: str) -> str:
    """Get all user-exposed parameters in a Niagara system.

    User parameters are the ones exposed to blueprints and material
    instances for runtime control.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    """
    try:
        data = _call_plugin(
            "NiagaraMCPParameterLibrary",
            "GetUserParameters",
            SystemPath=asset_path,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    params = data.get("parameters", [])
    if not params:
        return f"No user parameters found in {asset_path}."

    lines = [
        f"User Parameters: {asset_path}",
        "",
        f"  {'Name':<35} {'Type':<20} {'Default':<25}",
        f"  {'-'*35} {'-'*20} {'-'*25}",
    ]
    for p in params:
        name = p.get("name", "?")
        type_name = p.get("type", "?")
        default = str(p.get("default", ""))
        lines.append(f"  {name:<35} {type_name:<20} {default:<25}")

    return "\n".join(lines)
