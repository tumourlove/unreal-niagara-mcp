"""Niagara event inspection tools using UPROPERTY reads."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _escape_py_string, _format_error


# ---------------------------------------------------------------------------
# get_niagara_events
# ---------------------------------------------------------------------------

_EVENTS_SCRIPT = '''\
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
            events_out = []
            if emitter_inst is not None:
                ver_data = emitter_inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    try:
                        event_handlers = latest.get_editor_property("event_handler_script_props")
                        if event_handlers:
                            for idx, eh in enumerate(event_handlers):
                                ev = {{"index": idx}}
                                try:
                                    script = eh.get_editor_property("script")
                                    if script is not None:
                                        ev["script_name"] = script.get_name()
                                except Exception:
                                    pass
                                try:
                                    ev["source_event_name"] = str(eh.get_editor_property("source_event_name"))
                                except Exception:
                                    pass
                                try:
                                    ev["execution_mode"] = str(eh.get_editor_property("execution_mode"))
                                except Exception:
                                    pass
                                try:
                                    ev["spawn_number"] = int(eh.get_editor_property("spawn_number"))
                                except Exception:
                                    pass
                                try:
                                    ev["max_events_per_frame"] = int(eh.get_editor_property("max_events_per_frame"))
                                except Exception:
                                    pass
                                try:
                                    ev["use_random_spawn_number"] = bool(eh.get_editor_property("use_random_spawn_number"))
                                except Exception:
                                    pass
                                events_out.append(ev)
                    except Exception:
                        pass
            result["emitters"].append({{"name": name, "events": events_out}})
    print(json.dumps(result))
'''


@mcp.tool()
def get_niagara_events(asset_path: str, emitter_name: str = "") -> str:
    """Get event handlers configured in a Niagara system.

    Shows event source, execution mode, spawn count, and other
    event handler properties.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    emitter_name: Optional emitter name filter (empty = all emitters)
    """
    bridge = _get_bridge()
    escaped_path = _escape_py_string(asset_path)
    escaped_emitter = _escape_py_string(emitter_name or "")
    command = _EVENTS_SCRIPT.format(
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

    lines = [f"Event Handlers: {asset_path}", ""]
    total = 0
    for em in emitters:
        events = em.get("events", [])
        total += len(events)
        lines.append(f"Emitter: {em.get('name', '?')} ({len(events)} event handler(s))")
        if not events:
            lines.append("  (none)")
        for ev in events:
            lines.append(f"  [{ev.get('index', '?')}] {ev.get('source_event_name', '?')}")
            if ev.get("script_name"):
                lines.append(f"      Script: {ev['script_name']}")
            if ev.get("execution_mode"):
                lines.append(f"      Execution Mode: {ev['execution_mode']}")
            if "spawn_number" in ev:
                lines.append(f"      Spawn Number: {ev['spawn_number']}")
            if "max_events_per_frame" in ev:
                lines.append(f"      Max Events/Frame: {ev['max_events_per_frame']}")
            if ev.get("use_random_spawn_number"):
                lines.append(f"      Random Spawn: {ev['use_random_spawn_number']}")
        lines.append("")

    if total == 0:
        return f"No event handlers found in {asset_path}."

    return "\n".join(lines).rstrip()
