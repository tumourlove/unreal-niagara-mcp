"""Niagara system-level editing tools using pure Python UPROPERTY writes."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _escape_py_string, _format_error


# ---------------------------------------------------------------------------
# set_system_property
# ---------------------------------------------------------------------------

_SET_SYSTEM_PROP_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
prop = "{property_name}"
raw_value = "{value}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    try:
        # Parse value based on current property type
        current = system.get_editor_property(prop)
        if isinstance(current, bool):
            val = raw_value.lower() in ("true", "1", "yes")
        elif isinstance(current, int):
            val = int(raw_value)
        elif isinstance(current, float):
            val = float(raw_value)
        else:
            val = raw_value
        system.set_editor_property(prop, val)
        system.modify()
        print(json.dumps({{"status": "OK", "property": prop, "value": str(val)}}))
    except Exception as e:
        print(json.dumps({{"error": True, "message": str(e)}}))
'''


@mcp.tool()
def set_system_property(
    asset_path: str,
    property_name: str,
    value: str,
) -> str:
    """Set a top-level property on a Niagara system.

    Supports warmup_time, warmup_tick_count, warmup_tick_delta,
    determinism, fixed_tick_delta, fixed_tick_delta_time, and other
    UPROPERTY fields on UNiagaraSystem.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    property_name: Property name (e.g. 'warmup_time', 'determinism')
    value: New value as string (auto-parsed to matching type)
    """
    bridge = _get_bridge()
    command = _SET_SYSTEM_PROP_SCRIPT.format(
        asset_path=_escape_py_string(asset_path),
        property_name=_escape_py_string(property_name),
        value=_escape_py_string(value),
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

    return (
        f"Set system property:\n"
        f"  System: {asset_path}\n"
        f"  Property: {property_name}\n"
        f"  Value: {data.get('value', value)}\n"
        f"  Status: {data.get('status', 'OK')}"
    )


# ---------------------------------------------------------------------------
# set_scalability
# ---------------------------------------------------------------------------

_SET_SCALABILITY_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    try:
        changed = []
        scalability_overrides = "{scalability_json}"
        overrides = json.loads(scalability_overrides)
        for key, val in overrides.items():
            try:
                if isinstance(val, bool):
                    system.set_editor_property(key, val)
                elif isinstance(val, int):
                    system.set_editor_property(key, val)
                elif isinstance(val, float):
                    system.set_editor_property(key, val)
                else:
                    system.set_editor_property(key, str(val))
                changed.append(key)
            except Exception as e:
                pass
        system.modify()
        print(json.dumps({{"status": "OK", "changed": changed}}))
    except Exception as e:
        print(json.dumps({{"error": True, "message": str(e)}}))
'''


@mcp.tool()
def set_scalability(
    asset_path: str,
    warmup_time: str = "",
    warmup_tick_count: str = "",
    fixed_tick_delta: str = "",
    fixed_tick_delta_time: str = "",
    determinism: str = "",
) -> str:
    """Set multiple scalability and tick properties on a Niagara system at once.

    Only properties with non-empty values will be changed.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    warmup_time: Warmup time in seconds (float)
    warmup_tick_count: Number of warmup ticks (int)
    fixed_tick_delta: Whether to use fixed tick delta (true/false)
    fixed_tick_delta_time: Fixed tick delta time in seconds (float)
    determinism: Whether system is deterministic (true/false)
    """
    import json as _json

    overrides = {}
    if warmup_time:
        overrides["warmup_time"] = float(warmup_time)
    if warmup_tick_count:
        overrides["warmup_tick_count"] = int(warmup_tick_count)
    if fixed_tick_delta:
        overrides["fixed_tick_delta"] = fixed_tick_delta.lower() in ("true", "1", "yes")
    if fixed_tick_delta_time:
        overrides["fixed_tick_delta_time"] = float(fixed_tick_delta_time)
    if determinism:
        overrides["determinism"] = determinism.lower() in ("true", "1", "yes")

    if not overrides:
        return "No properties specified to change."

    bridge = _get_bridge()
    command = _SET_SCALABILITY_SCRIPT.format(
        asset_path=_escape_py_string(asset_path),
        scalability_json=_escape_py_string(_json.dumps(overrides)),
    )

    try:
        result = bridge.run_command(command, exec_mode="ExecuteFile")
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    if not result.get("success", False):
        return f"Error: {result.get('result', 'Command failed')}"

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
        data = _json.loads(output)
    except _json.JSONDecodeError:
        return f"Error: Invalid response from editor: {output[:300]}"

    err = _format_error(data)
    if err:
        return err

    changed = data.get("changed", [])
    lines = [
        f"Set scalability properties:",
        f"  System: {asset_path}",
    ]
    for key in changed:
        lines.append(f"  {key}: {overrides.get(key, '?')}")
    lines.append(f"  Status: {data.get('status', 'OK')}")

    return "\n".join(lines)
