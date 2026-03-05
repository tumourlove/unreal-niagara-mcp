"""Niagara search tools using asset registry queries via the editor bridge."""

from __future__ import annotations

import json

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _escape_py_string, _format_error


def _run_bridge_script(script: str) -> dict:
    """Run a Python script on the editor bridge and return parsed JSON.

    Returns a dict. On any failure the dict contains {"error": True, "message": ...}.
    """
    bridge = _get_bridge()
    result = bridge.run_command(script, exec_mode="ExecuteFile")

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
        output = str(result.get("result", "")).strip()

    json_start = output.find("{")
    json_list_start = output.find("[")
    if json_list_start >= 0 and (json_start < 0 or json_list_start < json_start):
        start = json_list_start
    elif json_start >= 0:
        start = json_start
    else:
        return {"error": True, "message": f"No JSON in response: {output[:300]}"}

    if start > 0:
        output = output[start:]

    try:
        parsed = json.loads(output)
        if isinstance(parsed, list):
            return {"items": parsed}
        return parsed
    except json.JSONDecodeError:
        return {"error": True, "message": f"Invalid JSON from editor: {output[:300]}"}


# ---------------------------------------------------------------------------
# search_niagara_systems
# ---------------------------------------------------------------------------

_SEARCH_SYSTEMS_SCRIPT = '''\
import unreal, json
registry = unreal.AssetRegistryHelpers.get_asset_registry()
filt = unreal.ARFilter()
try:
    filt.class_paths = [unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraSystem")]
except Exception:
    filt.class_names = ["NiagaraSystem"]
{folder_filter}
assets = registry.get_assets(filt)
results = []
filter_text = "{filter_text}".lower()
limit = {limit}
for a in assets:
    path = str(a.get_full_name()).split(" ", 1)[-1] if hasattr(a, "get_full_name") else str(a.package_name)
    try:
        path = str(a.package_name) + "." + str(a.asset_name)
    except Exception:
        pass
    if filter_text and filter_text not in path.lower():
        continue
    results.append(path)
    if len(results) >= limit:
        break
print(json.dumps({{"count": len(results), "systems": results}}))
'''


@mcp.tool()
def search_niagara_systems(
    filter_text: str = "",
    folder: str = "",
    limit: int = 50,
) -> str:
    """Search for Niagara systems in the project by name or folder.

    filter_text: Optional text to filter asset names (case-insensitive)
    folder: Optional folder path to restrict search, e.g. '/Game/VFX'
    limit: Maximum number of results (default 50)
    """
    folder_filter = ""
    if folder:
        escaped_folder = _escape_py_string(folder)
        folder_filter = f'filt.package_paths = [unreal.Name("{escaped_folder}")]'
    escaped_filter = _escape_py_string(filter_text or "")
    script = _SEARCH_SYSTEMS_SCRIPT.format(
        filter_text=escaped_filter,
        folder_filter=folder_filter,
        limit=int(limit),
    )

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    systems = data.get("systems", [])
    if not systems:
        return "No Niagara systems found matching the criteria."

    lines = [f"Niagara Systems ({data.get('count', len(systems))}):", ""]
    for i, s in enumerate(systems):
        lines.append(f"  [{i}] {s}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# search_niagara_modules
# ---------------------------------------------------------------------------

_SEARCH_MODULES_SCRIPT = '''\
import unreal, json
registry = unreal.AssetRegistryHelpers.get_asset_registry()
filt = unreal.ARFilter()
try:
    filt.class_paths = [unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraScript")]
except Exception:
    filt.class_names = ["NiagaraScript"]
{folder_filter}
assets = registry.get_assets(filt)
results = []
filter_text = "{filter_text}".lower()
limit = {limit}
for a in assets:
    try:
        path = str(a.package_name) + "." + str(a.asset_name)
    except Exception:
        path = str(a.package_name)
    if filter_text and filter_text not in path.lower():
        continue
    results.append(path)
    if len(results) >= limit:
        break
print(json.dumps({{"count": len(results), "modules": results}}))
'''


@mcp.tool()
def search_niagara_modules(
    filter_text: str = "",
    folder: str = "",
    limit: int = 50,
) -> str:
    """Search for Niagara module scripts in the project.

    filter_text: Optional text to filter module names (case-insensitive)
    folder: Optional folder path to restrict search
    limit: Maximum number of results (default 50)
    """
    folder_filter = ""
    if folder:
        escaped_folder = _escape_py_string(folder)
        folder_filter = f'filt.package_paths = [unreal.Name("{escaped_folder}")]'
    escaped_filter = _escape_py_string(filter_text or "")
    script = _SEARCH_MODULES_SCRIPT.format(
        filter_text=escaped_filter,
        folder_filter=folder_filter,
        limit=int(limit),
    )

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    modules = data.get("modules", [])
    if not modules:
        return "No Niagara modules found matching the criteria."

    lines = [f"Niagara Modules ({data.get('count', len(modules))}):", ""]
    for i, m in enumerate(modules):
        lines.append(f"  [{i}] {m}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# search_by_data_interface
# ---------------------------------------------------------------------------

_SEARCH_DI_SCRIPT = '''\
import unreal, json
registry = unreal.AssetRegistryHelpers.get_asset_registry()
filt = unreal.ARFilter()
try:
    filt.class_paths = [unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraSystem")]
except Exception:
    filt.class_names = ["NiagaraSystem"]
{folder_filter}
assets = registry.get_assets(filt)
di_class = "{di_class_name}"
limit = {limit}
results = []
for a in assets:
    try:
        path = str(a.package_name) + "." + str(a.asset_name)
    except Exception:
        path = str(a.package_name)
    system = unreal.load_asset(str(a.package_name))
    if system is None:
        continue
    handles = system.get_editor_property("emitter_handles")
    if not handles:
        continue
    found = False
    for h in handles:
        inst = h.get_editor_property("instance")
        if inst is None:
            continue
        ver_data = inst.get_editor_property("versioned_emitter_data")
        if not ver_data or len(ver_data) == 0:
            continue
        latest = ver_data[-1]
        try:
            scripts = latest.get_editor_property("scratch_pad_scripts")
            if scripts:
                for s in scripts:
                    dis = s.get_editor_property("provided_dependencies")
                    if dis:
                        for d in dis:
                            if di_class in type(d).__name__:
                                found = True
                                break
                    if found:
                        break
        except Exception:
            pass
        if not found:
            try:
                di_props = latest.get_editor_property("data_interfaces")
                if di_props:
                    for d in di_props:
                        if di_class in type(d).__name__:
                            found = True
                            break
            except Exception:
                pass
        if found:
            break
    if found:
        results.append(path)
        if len(results) >= limit:
            break
print(json.dumps({{"di_class": di_class, "count": len(results), "systems": results}}))
'''


@mcp.tool()
def search_by_data_interface(
    di_class_name: str,
    folder: str = "",
    limit: int = 50,
) -> str:
    """Search for Niagara systems that use a specific Data Interface class.

    This is more expensive than name-based search as it loads each system.

    di_class_name: Data Interface class name, e.g. 'NiagaraDataInterfaceCurve'
    folder: Optional folder to restrict search
    limit: Maximum results (default 50)
    """
    folder_filter = ""
    if folder:
        escaped_folder = _escape_py_string(folder)
        folder_filter = f'filt.package_paths = [unreal.Name("{escaped_folder}")]'
    escaped_di = _escape_py_string(di_class_name)
    script = _SEARCH_DI_SCRIPT.format(
        di_class_name=escaped_di,
        folder_filter=folder_filter,
        limit=int(limit),
    )

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    systems = data.get("systems", [])
    if not systems:
        return f"No systems found using data interface '{di_class_name}'."

    lines = [
        f"Systems using Data Interface '{data.get('di_class', di_class_name)}'",
        f"Found: {data.get('count', len(systems))}",
        "",
    ]
    for i, s in enumerate(systems):
        lines.append(f"  [{i}] {s}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# search_by_parameter
# ---------------------------------------------------------------------------

_SEARCH_PARAM_SCRIPT = '''\
import unreal, json
registry = unreal.AssetRegistryHelpers.get_asset_registry()
filt = unreal.ARFilter()
try:
    filt.class_paths = [unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraSystem")]
except Exception:
    filt.class_names = ["NiagaraSystem"]
{folder_filter}
assets = registry.get_assets(filt)
param_name = "{parameter_name}"
limit = {limit}
results = []
for a in assets:
    try:
        path = str(a.package_name) + "." + str(a.asset_name)
    except Exception:
        path = str(a.package_name)
    system = unreal.load_asset(str(a.package_name))
    if system is None:
        continue
    try:
        user_params = system.get_editor_property("exposed_parameters")
        if user_params is not None:
            params = user_params.get_editor_property("parameters")
            if params:
                for p in params:
                    name = str(p.get_editor_property("name"))
                    if param_name.lower() in name.lower():
                        results.append({{"path": path, "param_name": name}})
                        break
    except Exception:
        pass
    if len(results) >= limit:
        break
print(json.dumps({{"parameter_name": param_name, "count": len(results), "systems": results}}))
'''


@mcp.tool()
def search_by_parameter(
    parameter_name: str,
    folder: str = "",
    limit: int = 50,
) -> str:
    """Search for Niagara systems that expose a user parameter with a given name.

    parameter_name: Parameter name to search for (case-insensitive partial match)
    folder: Optional folder to restrict search
    limit: Maximum results (default 50)
    """
    folder_filter = ""
    if folder:
        escaped_folder = _escape_py_string(folder)
        folder_filter = f'filt.package_paths = [unreal.Name("{escaped_folder}")]'
    escaped_param = _escape_py_string(parameter_name)
    script = _SEARCH_PARAM_SCRIPT.format(
        parameter_name=escaped_param,
        folder_filter=folder_filter,
        limit=int(limit),
    )

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    systems = data.get("systems", [])
    if not systems:
        return f"No systems found with parameter matching '{parameter_name}'."

    lines = [
        f"Systems with parameter matching '{data.get('parameter_name', parameter_name)}'",
        f"Found: {data.get('count', len(systems))}",
        "",
    ]
    for i, s in enumerate(systems):
        lines.append(f"  [{i}] {s.get('path', '?')} (param: {s.get('param_name', '?')})")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# search_by_material
# ---------------------------------------------------------------------------

_SEARCH_MATERIAL_SCRIPT = '''\
import unreal, json
registry = unreal.AssetRegistryHelpers.get_asset_registry()
filt = unreal.ARFilter()
try:
    filt.class_paths = [unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraSystem")]
except Exception:
    filt.class_names = ["NiagaraSystem"]
{folder_filter}
assets = registry.get_assets(filt)
mat_path = "{material_path}"
limit = {limit}
results = []
for a in assets:
    try:
        path = str(a.package_name) + "." + str(a.asset_name)
    except Exception:
        path = str(a.package_name)
    system = unreal.load_asset(str(a.package_name))
    if system is None:
        continue
    handles = system.get_editor_property("emitter_handles")
    if not handles:
        continue
    found = False
    for h in handles:
        inst = h.get_editor_property("instance")
        if inst is None:
            continue
        ver_data = inst.get_editor_property("versioned_emitter_data")
        if not ver_data or len(ver_data) == 0:
            continue
        latest = ver_data[-1]
        try:
            renderers = latest.get_editor_property("renderer_properties")
            if renderers:
                for r in renderers:
                    try:
                        mat = r.get_editor_property("material")
                        if mat is not None and mat_path in mat.get_path_name():
                            found = True
                            break
                    except Exception:
                        pass
        except Exception:
            pass
        if found:
            break
    if found:
        results.append(path)
        if len(results) >= limit:
            break
print(json.dumps({{"material": mat_path, "count": len(results), "systems": results}}))
'''


@mcp.tool()
def search_by_material(
    material_path: str,
    folder: str = "",
    limit: int = 50,
) -> str:
    """Search for Niagara systems that reference a specific material in renderers.

    material_path: Material asset path or partial path to match
    folder: Optional folder to restrict search
    limit: Maximum results (default 50)
    """
    folder_filter = ""
    if folder:
        escaped_folder = _escape_py_string(folder)
        folder_filter = f'filt.package_paths = [unreal.Name("{escaped_folder}")]'
    escaped_mat = _escape_py_string(material_path)
    script = _SEARCH_MATERIAL_SCRIPT.format(
        material_path=escaped_mat,
        folder_filter=folder_filter,
        limit=int(limit),
    )

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    systems = data.get("systems", [])
    if not systems:
        return f"No systems found using material '{material_path}'."

    lines = [
        f"Systems using material '{data.get('material', material_path)}'",
        f"Found: {data.get('count', len(systems))}",
        "",
    ]
    for i, s in enumerate(systems):
        lines.append(f"  [{i}] {s}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# find_niagara_references
# ---------------------------------------------------------------------------

_REFERENCES_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
registry = unreal.AssetRegistryHelpers.get_asset_registry()
limit = {limit}

referencers = []
try:
    deps = registry.get_referencers(path)
    if deps:
        for d in deps[:limit]:
            referencers.append(str(d))
except Exception:
    pass

dependencies = []
try:
    deps = registry.get_dependencies(path)
    if deps:
        for d in deps[:limit]:
            dependencies.append(str(d))
except Exception:
    pass

print(json.dumps({{
    "asset_path": path,
    "referencers": referencers,
    "referencer_count": len(referencers),
    "dependencies": dependencies,
    "dependency_count": len(dependencies),
}}))
'''


@mcp.tool()
def find_niagara_references(asset_path: str, limit: int = 50) -> str:
    """Find what references or is referenced by a Niagara asset.

    Shows both incoming references (who uses this asset) and
    outgoing dependencies (what this asset uses).

    asset_path: Full Unreal asset path, e.g. '/Game/VFX/NS_Fire'
    limit: Maximum references in each direction (default 50)
    """
    escaped = _escape_py_string(asset_path)
    script = _REFERENCES_SCRIPT.format(asset_path=escaped, limit=int(limit))

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    lines = [f"References for: {data.get('asset_path', asset_path)}", ""]

    referencers = data.get("referencers", [])
    lines.append(f"Referenced By ({data.get('referencer_count', len(referencers))}):")
    if referencers:
        for r in referencers:
            lines.append(f"  - {r}")
    else:
        lines.append("  (none)")

    lines.append("")

    dependencies = data.get("dependencies", [])
    lines.append(f"Depends On ({data.get('dependency_count', len(dependencies))}):")
    if dependencies:
        for d in dependencies:
            lines.append(f"  - {d}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# compare_niagara_systems
# ---------------------------------------------------------------------------

_COMPARE_SCRIPT = '''\
import unreal, json

def get_system_fingerprint(path):
    system = unreal.load_asset(path)
    if system is None:
        return None
    handles = system.get_editor_property("emitter_handles")
    emitters = []
    params = []
    if handles:
        for h in handles:
            name = str(h.get_editor_property("name"))
            inst = h.get_editor_property("instance")
            em_info = {{"name": name, "modules": [], "renderers": []}}
            if inst is not None:
                ver_data = inst.get_editor_property("versioned_emitter_data")
                if ver_data and len(ver_data) > 0:
                    latest = ver_data[-1]
                    try:
                        sim = latest.get_editor_property("sim_target")
                        em_info["sim_target"] = str(sim) if sim is not None else "Unknown"
                    except Exception:
                        pass
                    try:
                        renderers = latest.get_editor_property("renderer_properties")
                        if renderers:
                            for r in renderers:
                                em_info["renderers"].append(type(r).__name__)
                    except Exception:
                        pass
            emitters.append(em_info)
    try:
        user_params = system.get_editor_property("exposed_parameters")
        if user_params is not None:
            p_list = user_params.get_editor_property("parameters")
            if p_list:
                for p in p_list:
                    params.append(str(p.get_editor_property("name")))
    except Exception:
        pass
    return {{"emitters": emitters, "parameters": params}}

fp_a = get_system_fingerprint("{asset_path_a}")
fp_b = get_system_fingerprint("{asset_path_b}")
if fp_a is None:
    print(json.dumps({{"error": True, "message": "Cannot load system A: {asset_path_a}"}}))
elif fp_b is None:
    print(json.dumps({{"error": True, "message": "Cannot load system B: {asset_path_b}"}}))
else:
    print(json.dumps({{
        "system_a": "{asset_path_a}",
        "system_b": "{asset_path_b}",
        "fingerprint_a": fp_a,
        "fingerprint_b": fp_b,
    }}))
'''


@mcp.tool()
def compare_niagara_systems(asset_path_a: str, asset_path_b: str) -> str:
    """Compare two Niagara systems side-by-side.

    Shows differences in emitter count, module stacks, parameters,
    and renderers in a diff-style output.

    asset_path_a: First system path
    asset_path_b: Second system path
    """
    escaped_a = _escape_py_string(asset_path_a)
    escaped_b = _escape_py_string(asset_path_b)
    script = _COMPARE_SCRIPT.format(asset_path_a=escaped_a, asset_path_b=escaped_b)

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    fp_a = data.get("fingerprint_a", {})
    fp_b = data.get("fingerprint_b", {})
    em_a = fp_a.get("emitters", [])
    em_b = fp_b.get("emitters", [])
    params_a = set(fp_a.get("parameters", []))
    params_b = set(fp_b.get("parameters", []))

    lines = [
        f"Comparison: {data.get('system_a', asset_path_a)}",
        f"       vs:  {data.get('system_b', asset_path_b)}",
        "",
        "--- Emitters ---",
        f"  System A: {len(em_a)} emitter(s)",
        f"  System B: {len(em_b)} emitter(s)",
        "",
    ]

    names_a = {e["name"] for e in em_a}
    names_b = {e["name"] for e in em_b}
    only_a = names_a - names_b
    only_b = names_b - names_a
    common = names_a & names_b

    if only_a:
        lines.append("  Only in A:")
        for n in sorted(only_a):
            lines.append(f"    - {n}")
    if only_b:
        lines.append("  Only in B:")
        for n in sorted(only_b):
            lines.append(f"    + {n}")
    if common:
        lines.append("  In Both:")
        for n in sorted(common):
            em_a_info = next((e for e in em_a if e["name"] == n), {})
            em_b_info = next((e for e in em_b if e["name"] == n), {})
            sim_a = em_a_info.get("sim_target", "?")
            sim_b = em_b_info.get("sim_target", "?")
            rend_a = em_a_info.get("renderers", [])
            rend_b = em_b_info.get("renderers", [])
            diffs = []
            if sim_a != sim_b:
                diffs.append(f"sim: {sim_a} -> {sim_b}")
            if rend_a != rend_b:
                diffs.append(f"renderers: {rend_a} -> {rend_b}")
            suffix = f" ({', '.join(diffs)})" if diffs else ""
            lines.append(f"    = {n}{suffix}")

    lines.append("")
    lines.append("--- Parameters ---")
    only_pa = params_a - params_b
    only_pb = params_b - params_a
    common_p = params_a & params_b

    if only_pa:
        for p in sorted(only_pa):
            lines.append(f"  - {p}  (only in A)")
    if only_pb:
        for p in sorted(only_pb):
            lines.append(f"  + {p}  (only in B)")
    if common_p:
        for p in sorted(common_p):
            lines.append(f"  = {p}  (in both)")
    if not params_a and not params_b:
        lines.append("  (no user parameters in either system)")

    return "\n".join(lines)
