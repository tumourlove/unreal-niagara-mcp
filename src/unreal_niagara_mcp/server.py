"""MCP server for Niagara particle system intelligence."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from unreal_niagara_mcp.editor_bridge import EditorBridge, EditorNotRunning

mcp = FastMCP(
    "unreal-niagara",
    instructions=(
        "Niagara particle system intelligence for Unreal Engine. "
        "Inspect, search, edit, create, and procedurally generate "
        "Niagara VFX systems, emitters, modules, and parameters."
    ),
)

_bridge: EditorBridge | None = None


def _reset_state() -> None:
    """Reset all singletons (for testing)."""
    global _bridge
    if _bridge:
        _bridge.disconnect()
    _bridge = None


def _get_bridge() -> EditorBridge:
    """Lazy-init the editor bridge."""
    global _bridge
    if _bridge is not None:
        return _bridge
    _bridge = EditorBridge(auto_connect=False)
    return _bridge


def _escape_py_string(s: str) -> str:
    """Escape a string for safe interpolation into a Python string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _call_plugin(lib_class: str, func_name: str, **kwargs: str) -> dict:
    """Call a C++ plugin function via the editor Python bridge.

    Args:
        lib_class: The UBlueprintFunctionLibrary subclass name
                   (e.g. 'NiagaraSystemLibrary').
        func_name: The UFUNCTION name on that class.
        **kwargs: String arguments to pass.

    Returns the parsed JSON response from the plugin.
    Raises EditorNotRunning if the editor is not available.
    """
    bridge = _get_bridge()

    args = ", ".join(
        f'{k}="{_escape_py_string(v)}"' for k, v in kwargs.items()
    )
    command = (
        "import unreal, json\n"
        f"result = unreal.{lib_class}.{func_name}({args})\n"
        "print(result)"
    )

    result = bridge.run_command(command, exec_mode="ExecuteFile")
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
        raw_result = result.get("result", "")
        output = str(raw_result).strip()

    json_start = output.find("{")
    if json_start > 0:
        output = output[json_start:]

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"error": True, "message": f"Invalid JSON from plugin: {output[:500]}"}


def _format_error(data: dict) -> str | None:
    """Return error message if data is an error response, else None."""
    if data.get("error"):
        return f"Error: {data.get('message', 'Unknown error')}"
    return None


# -- Register tool modules ---------------------------------------------------

import unreal_niagara_mcp.inspection.system_tools  # noqa: E402, F401


# -- Entry point -------------------------------------------------------------


def main() -> None:
    """Run the MCP server."""
    mcp.run()
