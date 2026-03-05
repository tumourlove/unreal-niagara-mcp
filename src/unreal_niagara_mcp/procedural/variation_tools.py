"""Effect variation generation tools for Niagara systems."""

from __future__ import annotations

import json

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _call_plugin, _escape_py_string, _format_error
from unreal_niagara_mcp.search.search_tools import _run_bridge_script


# ---------------------------------------------------------------------------
# Variation strategies
# ---------------------------------------------------------------------------

def _compute_color_shift_params(index: int, count: int, params: dict) -> dict:
    """Compute color shift parameters for a variation."""
    hue_range = float(params.get("hue_range", 360.0))
    saturation_factor = float(params.get("saturation_factor", 1.0))
    hue_offset = (hue_range / count) * index
    return {
        "hue_offset": round(hue_offset, 2),
        "saturation_factor": saturation_factor,
    }


def _compute_scale_params(index: int, count: int, params: dict) -> dict:
    """Compute scale variation parameters."""
    min_scale = float(params.get("min_scale", 0.5))
    max_scale = float(params.get("max_scale", 2.0))
    t = index / max(1, count - 1)
    scale = min_scale + t * (max_scale - min_scale)
    return {"scale_factor": round(scale, 3)}


def _compute_speed_params(index: int, count: int, params: dict) -> dict:
    """Compute speed variation parameters."""
    min_speed = float(params.get("min_speed", 0.5))
    max_speed = float(params.get("max_speed", 3.0))
    t = index / max(1, count - 1)
    speed = min_speed + t * (max_speed - min_speed)
    return {"speed_multiplier": round(speed, 3)}


def _compute_density_params(index: int, count: int, params: dict) -> dict:
    """Compute density (spawn rate) variation parameters."""
    min_density = float(params.get("min_density", 0.25))
    max_density = float(params.get("max_density", 4.0))
    t = index / max(1, count - 1)
    density = min_density + t * (max_density - min_density)
    return {"density_multiplier": round(density, 3)}


def _compute_combined_params(index: int, count: int, params: dict) -> dict:
    """Compute combined variation parameters (all dimensions at once)."""
    result = {}
    result.update(_compute_color_shift_params(index, count, params))
    result.update(_compute_scale_params(index, count, params))
    result.update(_compute_speed_params(index, count, params))
    result.update(_compute_density_params(index, count, params))
    return result


_VARIATION_STRATEGIES = {
    "color_shift": _compute_color_shift_params,
    "scale_range": _compute_scale_params,
    "speed_range": _compute_speed_params,
    "density_range": _compute_density_params,
    "combined": _compute_combined_params,
}


# ---------------------------------------------------------------------------
# Duplicate + modify script
# ---------------------------------------------------------------------------

_DUPLICATE_SCRIPT = '''\
import unreal, json
source = "{source_path}"
dest = "{dest_path}"
result = unreal.EditorAssetLibrary.duplicate_asset(source, dest)
if result:
    print(json.dumps({{"success": True, "path": dest}}))
else:
    print(json.dumps({{"error": True, "message": f"Failed to duplicate to {{dest}}"}}))
'''


@mcp.tool()
def generate_effect_variations(
    asset_path: str,
    variation_type: str,
    count: int = 3,
    variation_params: str = "",
) -> str:
    """Generate N variations of a Niagara system with systematically varied parameters.

    Creates duplicate systems with different parameter settings for
    rapid iteration and comparison.

    Available variation types:
      color_shift  - Vary hue across the color wheel
      scale_range  - Vary particle scale from small to large
      speed_range  - Vary particle velocity
      density_range - Vary spawn rate / density
      combined     - All of the above simultaneously

    asset_path: Source system to create variations from
    variation_type: Type of variation to apply
    count: Number of variations to create (default 3)
    variation_params: JSON object with type-specific params, e.g. '{"min_scale":0.5,"max_scale":3.0}'
    """
    strategy = _VARIATION_STRATEGIES.get(variation_type)
    if strategy is None:
        available = ", ".join(sorted(_VARIATION_STRATEGIES.keys()))
        return f"Unknown variation type '{variation_type}'. Available: {available}"

    params = {}
    if variation_params:
        try:
            params = json.loads(variation_params)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON for variation_params: {variation_params[:200]}"

    count = max(1, int(count))

    # Strip trailing numbers/suffix to create base name
    base_path = asset_path.rstrip("/")
    if base_path.endswith("'"):
        base_path = base_path[:-1]

    created = []
    failed = []

    for i in range(count):
        dest_path = f"{base_path}_Var{i + 1:02d}"
        var_params = strategy(i, count, params)

        # Step 1: Duplicate
        escaped_src = _escape_py_string(asset_path)
        escaped_dst = _escape_py_string(dest_path)
        dup_script = _DUPLICATE_SCRIPT.format(source_path=escaped_src, dest_path=escaped_dst)

        try:
            dup_data = _run_bridge_script(dup_script)
        except EditorNotRunning as e:
            return f"Editor not available: {e}"

        err = _format_error(dup_data)
        if err:
            failed.append({"path": dest_path, "error": err})
            continue

        # Step 2: Apply variation via batch ops
        ops = []
        for param_name, param_value in var_params.items():
            ops.append({
                "op": "set_variation_param",
                "asset_path": dest_path,
                "param_name": param_name,
                "value": str(param_value),
            })

        if ops:
            try:
                mod_data = _call_plugin(
                    "NiagaraBatchLibrary",
                    "BatchExecute",
                    Operations=json.dumps(ops),
                )
            except EditorNotRunning as e:
                failed.append({"path": dest_path, "error": f"Editor not available: {e}"})
                continue

            mod_err = _format_error(mod_data)
            if mod_err:
                # Duplication succeeded but modification failed -- still report
                created.append({"path": dest_path, "params": var_params, "warning": mod_err})
                continue

        created.append({"path": dest_path, "params": var_params})

    lines = [
        f"Effect Variations: {variation_type}",
        f"  Source: {asset_path}",
        f"  Requested: {count}",
        f"  Created: {len(created)}",
    ]
    if failed:
        lines.append(f"  Failed: {len(failed)}")
    lines.append("")

    for c in created:
        lines.append(f"  {c['path']}")
        for pk, pv in c["params"].items():
            lines.append(f"    {pk}: {pv}")
        if "warning" in c:
            lines.append(f"    Warning: {c['warning']}")
        lines.append("")

    if failed:
        lines.append("Failures:")
        for f in failed:
            lines.append(f"  {f['path']}: {f['error']}")

    return "\n".join(lines).rstrip()
