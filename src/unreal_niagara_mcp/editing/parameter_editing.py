"""Niagara parameter editing tools using C++ plugin calls."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _call_plugin, _format_error


# ---------------------------------------------------------------------------
# trace_parameter_bindings
# ---------------------------------------------------------------------------


@mcp.tool()
def trace_parameter_bindings(asset_path: str, parameter_name: str) -> str:
    """Trace where a Niagara parameter is read and written across the system.

    Shows which modules and stages reference this parameter,
    helping understand data flow through the system.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    parameter_name: Full parameter name, e.g. 'Particles.Velocity'
    """
    try:
        data = _call_plugin(
            "NiagaraMCPParameterLibrary",
            "TraceParameterBinding",
            SystemPath=asset_path,
            ParameterName=parameter_name,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    lines = [
        f"Parameter Trace: {parameter_name}",
        f"  System: {asset_path}",
        "",
    ]

    readers = data.get("readers", [])
    writers = data.get("writers", [])

    if writers:
        lines.append(f"Writers ({len(writers)}):")
        for w in writers:
            lines.append(f"  {w.get('emitter', 'System')}/{w.get('stage', '?')}: {w.get('module', '?')}")
        lines.append("")

    if readers:
        lines.append(f"Readers ({len(readers)}):")
        for r in readers:
            lines.append(f"  {r.get('emitter', 'System')}/{r.get('stage', '?')}: {r.get('module', '?')}")
        lines.append("")

    if not readers and not writers:
        lines.append("No references found for this parameter.")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# set_user_parameter_default
# ---------------------------------------------------------------------------


@mcp.tool()
def set_user_parameter_default(
    asset_path: str,
    parameter_name: str,
    value: str,
) -> str:
    """Set the default value of a user parameter.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    parameter_name: The user parameter name, e.g. 'User.SpawnRate'
    value: The new default value as a string (will be parsed by the plugin)
    """
    try:
        data = _call_plugin(
            "NiagaraMCPParameterLibrary",
            "SetParameterDefault",
            SystemPath=asset_path,
            ParameterName=parameter_name,
            Value=value,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Set parameter default:\n"
        f"  System: {asset_path}\n"
        f"  Parameter: {parameter_name}\n"
        f"  New Value: {value}\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# add_user_parameter
# ---------------------------------------------------------------------------


@mcp.tool()
def add_user_parameter(
    asset_path: str,
    name: str,
    type_name: str,
    default_value: str = "",
) -> str:
    """Add a new user parameter to a Niagara system.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    name: Parameter name (will be prefixed with 'User.' if not already)
    type_name: Niagara type name, e.g. 'Float', 'Vector', 'LinearColor'
    default_value: Optional default value as string
    """
    try:
        data = _call_plugin(
            "NiagaraMCPParameterLibrary",
            "AddUserParameter",
            SystemPath=asset_path,
            Name=name,
            TypeName=type_name,
            DefaultValue=default_value,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Added user parameter:\n"
        f"  System: {asset_path}\n"
        f"  Name: {data.get('name', name)}\n"
        f"  Type: {type_name}\n"
        f"  Default: {default_value or '(type default)'}"
    )


# ---------------------------------------------------------------------------
# remove_user_parameter
# ---------------------------------------------------------------------------


@mcp.tool()
def remove_user_parameter(asset_path: str, name: str) -> str:
    """Remove a user parameter from a Niagara system.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    name: The user parameter name to remove
    """
    try:
        data = _call_plugin(
            "NiagaraMCPParameterLibrary",
            "RemoveUserParameter",
            SystemPath=asset_path,
            Name=name,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Removed user parameter:\n"
        f"  System: {asset_path}\n"
        f"  Name: {name}\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# set_module_input
# ---------------------------------------------------------------------------


@mcp.tool()
def set_module_input(
    asset_path: str,
    emitter_name: str,
    module_name: str,
    input_name: str,
    value: str,
) -> str:
    """Set a module input value in a Niagara emitter.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: The emitter containing the module
    module_name: Name of the module
    input_name: Name of the input to set
    value: New value as string (parsed by the plugin based on input type)
    """
    try:
        data = _call_plugin(
            "NiagaraMCPModuleLibrary",
            "SetModuleInputValue",
            SystemPath=asset_path,
            EmitterName=emitter_name,
            ModuleName=module_name,
            InputName=input_name,
            Value=value,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    return (
        f"Set module input:\n"
        f"  System: {asset_path}\n"
        f"  Emitter: {emitter_name}\n"
        f"  Module: {module_name}\n"
        f"  Input: {input_name}\n"
        f"  New Value: {value}\n"
        f"  Status: {data.get('status', 'OK')}"
    )
