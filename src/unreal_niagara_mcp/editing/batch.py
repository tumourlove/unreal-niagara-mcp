"""Niagara batch editing tool using C++ BatchExecute."""

from __future__ import annotations

import json

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _call_plugin, _format_error


# ---------------------------------------------------------------------------
# batch_edit_niagara
# ---------------------------------------------------------------------------


@mcp.tool()
def batch_edit_niagara(
    asset_path: str,
    operations: list[dict],
) -> str:
    """Execute multiple editing operations on a Niagara system in a single transaction.

    Wraps all operations in a single undo transaction for atomicity.
    If any operation fails, the entire batch is rolled back.

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    operations: List of operation dicts, each with:
        - "op": operation name (e.g. "add_module", "set_input", "add_emitter")
        - Additional keys specific to each operation type

    Supported operations:
        add_module: {op, emitter, stage, module_path, index?}
        remove_module: {op, emitter, module_guid}
        set_input: {op, emitter, module, input, value}
        set_enabled: {op, emitter, module_guid, enabled}
        add_emitter: {op, emitter_asset_path, name?}
        remove_emitter: {op, emitter}
        set_parameter: {op, parameter, value}
        add_parameter: {op, name, type, default?}
        remove_parameter: {op, name}
        add_renderer: {op, emitter, renderer_class}
        remove_renderer: {op, emitter, renderer_index}
        set_renderer_material: {op, emitter, renderer_index, material_path}
        set_property: {op, emitter?, property, value}
    """
    try:
        data = _call_plugin(
            "NiagaraMCPBatchLibrary",
            "BatchExecute",
            SystemPath=asset_path,
            OperationsJson=json.dumps(operations),
        )
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    results = data.get("results", [])
    total = len(results)
    succeeded = sum(1 for r in results if r.get("success", False))
    failed = total - succeeded

    lines = [
        f"Batch Edit: {asset_path}",
        f"  Operations: {total} total, {succeeded} succeeded, {failed} failed",
        "",
    ]

    for i, r in enumerate(results):
        status = "OK" if r.get("success", False) else "FAILED"
        op_name = r.get("op", operations[i].get("op", "?") if i < len(operations) else "?")
        lines.append(f"  [{i}] {op_name}: {status}")
        if not r.get("success", False) and r.get("message"):
            lines.append(f"       Error: {r['message']}")

    if data.get("rolled_back"):
        lines.append("")
        lines.append("  ** Transaction was ROLLED BACK due to failures **")

    return "\n".join(lines)
