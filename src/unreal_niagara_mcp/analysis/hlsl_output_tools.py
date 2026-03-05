"""Niagara module graph and data interface function inspection tools."""

from __future__ import annotations

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _call_plugin, _format_error


# ---------------------------------------------------------------------------
# get_module_graph
# ---------------------------------------------------------------------------


@mcp.tool()
def get_module_graph(asset_path: str, emitter_name: str = "", module_name: str = "") -> str:
    """Get the node graph of a Niagara module script.

    If given a direct module script asset path (e.g. '/Game/VFX/Modules/MyModule'),
    inspects that module directly. If given a system path plus emitter and module
    names, resolves to the underlying module script first.

    Returns the graph structure: nodes, connections, and any custom HLSL expressions.

    asset_path: Unreal asset path - either a module script or a Niagara system
    emitter_name: Emitter containing the module (required if asset_path is a system)
    module_name: Module name within the emitter (required if asset_path is a system)
    """
    try:
        data = _call_plugin(
            "NiagaraMCPAnalysisLibrary",
            "GetModuleGraph",
            AssetPath=asset_path,
            EmitterName=emitter_name or "",
            ModuleName=module_name or "",
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    script_path = data.get("script_path", asset_path)
    nodes = data.get("nodes", [])
    connections = data.get("connections", [])
    hlsl_expressions = data.get("hlsl_expressions", [])

    lines = [
        f"Module Graph: {data.get('module_name', script_path)}",
        f"Script: {script_path}",
        "",
    ]

    if nodes:
        lines.append(f"Nodes ({len(nodes)}):")
        for n in nodes:
            node_type = n.get("type", "?")
            node_name = n.get("name", "?")
            lines.append(f"  [{n.get('id', '?')}] {node_type}: {node_name}")
            if n.get("inputs"):
                for inp in n["inputs"]:
                    lines.append(f"       Input:  {inp.get('name', '?')} ({inp.get('type', '?')})")
            if n.get("outputs"):
                for out in n["outputs"]:
                    lines.append(f"       Output: {out.get('name', '?')} ({out.get('type', '?')})")
        lines.append("")

    if connections:
        lines.append(f"Connections ({len(connections)}):")
        for c in connections:
            src = f"{c.get('source_node', '?')}.{c.get('source_pin', '?')}"
            dst = f"{c.get('target_node', '?')}.{c.get('target_pin', '?')}"
            lines.append(f"  {src} -> {dst}")
        lines.append("")

    if hlsl_expressions:
        lines.append("Custom HLSL Expressions:")
        for h in hlsl_expressions:
            lines.append(f"  Node: {h.get('node_name', '?')}")
            lines.append(f"  --- HLSL ---")
            hlsl_code = h.get("code", "")
            for code_line in hlsl_code.split("\n"):
                lines.append(f"  {code_line}")
            lines.append(f"  --- END ---")
            lines.append("")

    if not nodes and not connections:
        lines.append("(No graph data available - module may be a built-in or compiled module)")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# get_di_functions
# ---------------------------------------------------------------------------


@mcp.tool()
def get_di_functions(di_class_name: str) -> str:
    """Get all functions available on a Niagara data interface class.

    Returns the function signatures, parameter types, and descriptions
    for all functions exposed by the specified data interface.

    di_class_name: The data interface class name, e.g. 'NiagaraDataInterfaceCurve'
                   or 'UNiagaraDataInterfaceSkeletalMesh'
    """
    try:
        data = _call_plugin(
            "NiagaraMCPAnalysisLibrary",
            "GetDataInterfaceFunctions",
            DIClassName=di_class_name,
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    functions = data.get("functions", [])
    class_name = data.get("class_name", di_class_name)

    lines = [
        f"Data Interface Functions: {class_name}",
        f"Total: {len(functions)} function(s)",
        "",
    ]

    if not functions:
        lines.append("No functions found for this data interface.")
        return "\n".join(lines)

    for fn in functions:
        fn_name = fn.get("name", "?")
        return_type = fn.get("return_type", "void")
        params = fn.get("parameters", [])

        param_strs = []
        for p in params:
            p_type = p.get("type", "?")
            p_name = p.get("name", "?")
            p_dir = p.get("direction", "in")
            dir_prefix = "out " if p_dir == "out" else "inout " if p_dir == "inout" else ""
            param_strs.append(f"{dir_prefix}{p_type} {p_name}")

        signature = f"{return_type} {fn_name}({', '.join(param_strs)})"
        lines.append(f"  {signature}")

        if fn.get("description"):
            lines.append(f"    // {fn['description']}")
        lines.append("")

    return "\n".join(lines).rstrip()
