"""Niagara discovery and analytics tools for project-wide VFX intelligence."""

from __future__ import annotations

import json
import re

from unreal_niagara_mcp.editor_bridge import EditorNotRunning
from unreal_niagara_mcp.server import mcp, _get_bridge, _escape_py_string, _format_error
from unreal_niagara_mcp.search.search_tools import _run_bridge_script


# ---------------------------------------------------------------------------
# find_similar_systems
# ---------------------------------------------------------------------------

_SIMILAR_SCRIPT = '''\
import unreal, json

def get_module_fingerprint(system):
    modules = set()
    handles = system.get_editor_property("emitter_handles")
    if not handles:
        return modules
    for h in handles:
        inst = h.get_editor_property("instance")
        if inst is None:
            continue
        ver_data = inst.get_editor_property("versioned_emitter_data")
        if not ver_data or len(ver_data) == 0:
            continue
        latest = ver_data[-1]
        for stage in ["emitter_spawn_script_props", "emitter_update_script_props",
                       "particle_spawn_script_props", "particle_update_script_props"]:
            try:
                props = latest.get_editor_property(stage)
                if props is not None:
                    script = props.get_editor_property("script")
                    if script is not None:
                        modules.add(script.get_path_name())
            except Exception:
                pass
    return modules

path = "{asset_path}"
target = unreal.load_asset(path)
if target is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    target_fp = get_module_fingerprint(target)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    filt = unreal.ARFilter()
    try:
        filt.class_paths = [unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraSystem")]
    except Exception:
        filt.class_names = ["NiagaraSystem"]
    assets = registry.get_assets(filt)
    threshold = {threshold}
    limit = {limit}
    similarities = []
    for a in assets:
        try:
            a_path = str(a.package_name) + "." + str(a.asset_name)
        except Exception:
            a_path = str(a.package_name)
        if a_path == path:
            continue
        sys_obj = unreal.load_asset(str(a.package_name))
        if sys_obj is None:
            continue
        other_fp = get_module_fingerprint(sys_obj)
        if not target_fp and not other_fp:
            continue
        union = target_fp | other_fp
        inter = target_fp & other_fp
        jaccard = len(inter) / len(union) if len(union) > 0 else 0.0
        if jaccard >= threshold:
            similarities.append({{"path": a_path, "similarity": round(jaccard, 3)}})
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    similarities = similarities[:limit]
    print(json.dumps({{"asset_path": path, "module_count": len(target_fp), "matches": similarities}}))
'''


@mcp.tool()
def find_similar_systems(
    asset_path: str,
    threshold: float = 0.5,
    limit: int = 10,
) -> str:
    """Find Niagara systems similar to a given one based on shared modules.

    Uses Jaccard similarity on the set of module scripts used by each system.
    Higher threshold = more similar.

    asset_path: Reference system to compare against
    threshold: Minimum similarity score 0.0-1.0 (default 0.5)
    limit: Maximum results (default 10)
    """
    escaped = _escape_py_string(asset_path)
    script = _SIMILAR_SCRIPT.format(
        asset_path=escaped,
        threshold=float(threshold),
        limit=int(limit),
    )

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    matches = data.get("matches", [])
    if not matches:
        return (
            f"No systems found with similarity >= {threshold} to "
            f"{data.get('asset_path', asset_path)}."
        )

    lines = [
        f"Systems similar to: {data.get('asset_path', asset_path)}",
        f"Reference modules: {data.get('module_count', '?')}",
        f"Threshold: {threshold}",
        "",
    ]
    for i, m in enumerate(matches):
        bar_len = int(m["similarity"] * 20)
        bar = "#" * bar_len + "." * (20 - bar_len)
        lines.append(f"  [{i}] {m['similarity']:.1%} [{bar}] {m['path']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# get_module_usage_map
# ---------------------------------------------------------------------------

_USAGE_MAP_SCRIPT = '''\
import unreal, json
registry = unreal.AssetRegistryHelpers.get_asset_registry()
filt = unreal.ARFilter()
try:
    filt.class_paths = [unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraSystem")]
except Exception:
    filt.class_names = ["NiagaraSystem"]
{folder_filter}
assets = registry.get_assets(filt)
limit = {limit}
usage = {{}}
system_count = 0
for a in assets:
    if system_count >= limit:
        break
    system = unreal.load_asset(str(a.package_name))
    if system is None:
        continue
    system_count += 1
    handles = system.get_editor_property("emitter_handles")
    if not handles:
        continue
    for h in handles:
        inst = h.get_editor_property("instance")
        if inst is None:
            continue
        ver_data = inst.get_editor_property("versioned_emitter_data")
        if not ver_data or len(ver_data) == 0:
            continue
        latest = ver_data[-1]
        for stage in ["emitter_spawn_script_props", "emitter_update_script_props",
                       "particle_spawn_script_props", "particle_update_script_props"]:
            try:
                props = latest.get_editor_property(stage)
                if props is not None:
                    script = props.get_editor_property("script")
                    if script is not None:
                        sp = script.get_path_name()
                        usage[sp] = usage.get(sp, 0) + 1
            except Exception:
                pass
sorted_usage = sorted(usage.items(), key=lambda x: x[1], reverse=True)
print(json.dumps({{"systems_scanned": system_count, "unique_modules": len(sorted_usage),
    "modules": [{{  "path": k, "count": v}} for k, v in sorted_usage]}}))
'''


@mcp.tool()
def get_module_usage_map(folder: str = "", limit: int = 100) -> str:
    """Get a usage map of all Niagara modules across systems in the project.

    Shows which modules are most commonly used and how many systems reference them.

    folder: Optional folder to restrict scan
    limit: Maximum systems to scan (default 100)
    """
    folder_filter = ""
    if folder:
        escaped_folder = _escape_py_string(folder)
        folder_filter = f'filt.package_paths = [unreal.Name("{escaped_folder}")]'
    script = _USAGE_MAP_SCRIPT.format(folder_filter=folder_filter, limit=int(limit))

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    modules = data.get("modules", [])
    lines = [
        f"Module Usage Map",
        f"Systems scanned: {data.get('systems_scanned', '?')}",
        f"Unique modules: {data.get('unique_modules', len(modules))}",
        "",
        "  Count  Module",
        "  -----  ------",
    ]
    for m in modules:
        lines.append(f"  {m['count']:5d}  {m['path']}")

    if not modules:
        lines.append("  (no modules found)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# get_niagara_inventory
# ---------------------------------------------------------------------------

_INVENTORY_SCRIPT = '''\
import unreal, json
registry = unreal.AssetRegistryHelpers.get_asset_registry()
filt = unreal.ARFilter()
try:
    filt.class_paths = [unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraSystem")]
except Exception:
    filt.class_names = ["NiagaraSystem"]
{folder_filter}
assets = registry.get_assets(filt)

total_systems = 0
total_emitters = 0
gpu_emitters = 0
cpu_emitters = 0
unique_modules = set()
unique_dis = set()
renderer_types = {{}}

for a in assets:
    system = unreal.load_asset(str(a.package_name))
    if system is None:
        continue
    total_systems += 1
    handles = system.get_editor_property("emitter_handles")
    if not handles:
        continue
    for h in handles:
        total_emitters += 1
        inst = h.get_editor_property("instance")
        if inst is None:
            continue
        ver_data = inst.get_editor_property("versioned_emitter_data")
        if not ver_data or len(ver_data) == 0:
            continue
        latest = ver_data[-1]
        try:
            sim = str(latest.get_editor_property("sim_target"))
            if "GPU" in sim:
                gpu_emitters += 1
            else:
                cpu_emitters += 1
        except Exception:
            cpu_emitters += 1
        for stage in ["emitter_spawn_script_props", "emitter_update_script_props",
                       "particle_spawn_script_props", "particle_update_script_props"]:
            try:
                props = latest.get_editor_property(stage)
                if props is not None:
                    script = props.get_editor_property("script")
                    if script is not None:
                        unique_modules.add(script.get_path_name())
            except Exception:
                pass
        try:
            renderers = latest.get_editor_property("renderer_properties")
            if renderers:
                for r in renderers:
                    rclass = type(r).__name__
                    renderer_types[rclass] = renderer_types.get(rclass, 0) + 1
        except Exception:
            pass

print(json.dumps({{
    "total_systems": total_systems,
    "total_emitters": total_emitters,
    "gpu_emitters": gpu_emitters,
    "cpu_emitters": cpu_emitters,
    "unique_modules": len(unique_modules),
    "unique_data_interfaces": len(unique_dis),
    "renderer_types": renderer_types,
}}))
'''


@mcp.tool()
def get_niagara_inventory(folder: str = "") -> str:
    """Get a comprehensive inventory summary of all Niagara assets in the project.

    Shows totals for systems, emitters, modules, data interfaces,
    GPU vs CPU breakdown, and renderer type distribution.

    folder: Optional folder to restrict inventory
    """
    folder_filter = ""
    if folder:
        escaped_folder = _escape_py_string(folder)
        folder_filter = f'filt.package_paths = [unreal.Name("{escaped_folder}")]'
    script = _INVENTORY_SCRIPT.format(folder_filter=folder_filter)

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    renderer_types = data.get("renderer_types", {})
    lines = [
        "Niagara Inventory",
        "=================",
        "",
        f"  Total Systems:          {data.get('total_systems', 0)}",
        f"  Total Emitters:         {data.get('total_emitters', 0)}",
        f"    CPU Emitters:         {data.get('cpu_emitters', 0)}",
        f"    GPU Emitters:         {data.get('gpu_emitters', 0)}",
        f"  Unique Modules:         {data.get('unique_modules', 0)}",
        f"  Unique Data Interfaces: {data.get('unique_data_interfaces', 0)}",
        "",
        "Renderer Types:",
    ]
    if renderer_types:
        for rclass, count in sorted(renderer_types.items(), key=lambda x: -x[1]):
            lines.append(f"  {count:5d}  {rclass}")
    else:
        lines.append("  (none found)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# query_niagara
# ---------------------------------------------------------------------------

_QUERY_SCRIPT = '''\
import unreal, json
registry = unreal.AssetRegistryHelpers.get_asset_registry()
filt = unreal.ARFilter()
try:
    filt.class_paths = [unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraSystem")]
except Exception:
    filt.class_names = ["NiagaraSystem"]
assets = registry.get_assets(filt)
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
    emitter_count = len(handles) if handles else 0

    sim_targets = []
    module_paths = []
    has_renderers = []
    if handles:
        for h in handles:
            inst = h.get_editor_property("instance")
            if inst is None:
                continue
            ver_data = inst.get_editor_property("versioned_emitter_data")
            if not ver_data or len(ver_data) == 0:
                continue
            latest = ver_data[-1]
            try:
                sim = str(latest.get_editor_property("sim_target"))
                sim_targets.append(sim)
            except Exception:
                pass
            for stage in ["emitter_spawn_script_props", "emitter_update_script_props",
                           "particle_spawn_script_props", "particle_update_script_props"]:
                try:
                    props = latest.get_editor_property(stage)
                    if props is not None:
                        script = props.get_editor_property("script")
                        if script is not None:
                            module_paths.append(script.get_path_name())
                except Exception:
                    pass
            try:
                renderers = latest.get_editor_property("renderer_properties")
                if renderers:
                    for r in renderers:
                        has_renderers.append(type(r).__name__)
            except Exception:
                pass

    info = {{
        "path": path,
        "emitter_count": emitter_count,
        "sim_targets": sim_targets,
        "modules": module_paths,
        "renderers": has_renderers,
    }}
    results.append(info)

print(json.dumps({{"systems": results}}))
'''


def _parse_query(query_string: str) -> list[dict]:
    """Parse a mini query language into filter conditions.

    Supported syntax:
      emitters>3
      emitters<5
      emitters=2
      sim_target=GPU
      has_module=SpawnRate
      has_renderer=Sprite
    Conditions joined by AND (case-insensitive).
    """
    conditions = []
    parts = re.split(r'\s+AND\s+', query_string, flags=re.IGNORECASE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # emitters>3, emitters<5, emitters=2
        m = re.match(r'emitters\s*([><=!]+)\s*(\d+)', part, re.IGNORECASE)
        if m:
            conditions.append({"field": "emitters", "op": m.group(1), "value": int(m.group(2))})
            continue
        # sim_target=GPU
        m = re.match(r'sim_target\s*=\s*(\S+)', part, re.IGNORECASE)
        if m:
            conditions.append({"field": "sim_target", "op": "=", "value": m.group(1)})
            continue
        # has_module=SpawnRate
        m = re.match(r'has_module\s*=\s*(\S+)', part, re.IGNORECASE)
        if m:
            conditions.append({"field": "has_module", "op": "contains", "value": m.group(1)})
            continue
        # has_renderer=Sprite
        m = re.match(r'has_renderer\s*=\s*(\S+)', part, re.IGNORECASE)
        if m:
            conditions.append({"field": "has_renderer", "op": "contains", "value": m.group(1)})
            continue

    return conditions


def _evaluate_conditions(system: dict, conditions: list[dict]) -> bool:
    """Evaluate all conditions against a system info dict."""
    for cond in conditions:
        field = cond["field"]
        op = cond["op"]
        value = cond["value"]

        if field == "emitters":
            count = system.get("emitter_count", 0)
            if op == ">" and not (count > value):
                return False
            elif op == ">=" and not (count >= value):
                return False
            elif op == "<" and not (count < value):
                return False
            elif op == "<=" and not (count <= value):
                return False
            elif op == "=" and not (count == value):
                return False
            elif op == "!=" and not (count != value):
                return False

        elif field == "sim_target":
            targets = system.get("sim_targets", [])
            if not any(str(value).lower() in t.lower() for t in targets):
                return False

        elif field == "has_module":
            modules = system.get("modules", [])
            if not any(str(value).lower() in m.lower() for m in modules):
                return False

        elif field == "has_renderer":
            renderers = system.get("renderers", [])
            if not any(str(value).lower() in r.lower() for r in renderers):
                return False

    return True


@mcp.tool()
def query_niagara(query_string: str) -> str:
    """Query Niagara systems with a mini query language.

    Supports conditions joined by AND:
      emitters>3 AND sim_target=GPU AND has_module=SpawnRate

    Condition types:
      emitters>N / emitters<N / emitters=N  (emitter count)
      sim_target=GPU / sim_target=CPU       (simulation target)
      has_module=<name>                      (module path contains name)
      has_renderer=<name>                    (renderer class contains name)

    query_string: The query, e.g. 'emitters>2 AND sim_target=GPU'
    """
    conditions = _parse_query(query_string)
    if not conditions:
        return f"Could not parse query: '{query_string}'. Use format: emitters>3 AND sim_target=GPU"

    try:
        data = _run_bridge_script(_QUERY_SCRIPT)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    systems = data.get("systems", [])
    matches = [s for s in systems if _evaluate_conditions(s, conditions)]

    if not matches:
        return f"No systems match query: '{query_string}'"

    lines = [
        f"Query: {query_string}",
        f"Matches: {len(matches)}",
        "",
    ]
    for i, s in enumerate(matches):
        targets = ", ".join(set(s.get("sim_targets", []))) or "?"
        lines.append(
            f"  [{i}] {s['path']} "
            f"(emitters={s['emitter_count']}, sim={targets})"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# trace_effect_lineage
# ---------------------------------------------------------------------------

_LINEAGE_SCRIPT = '''\
import unreal, json
path = "{asset_path}"
system = unreal.load_asset(path)
if system is None:
    print(json.dumps({{"error": True, "message": f"Cannot load asset: {{path}}"}}))
else:
    lineage = [path]
    current = system
    seen = set()
    seen.add(path)
    while True:
        try:
            template_id = current.get_editor_property("template_asset_description")
            if template_id and str(template_id) not in seen:
                lineage.append(str(template_id))
                seen.add(str(template_id))
                parent = unreal.load_asset(str(template_id))
                if parent is not None:
                    current = parent
                    continue
        except Exception:
            pass
        break
    print(json.dumps({{"asset_path": path, "lineage": lineage, "depth": len(lineage)}}))
'''


@mcp.tool()
def trace_effect_lineage(asset_path: str) -> str:
    """Trace the template/parent chain of a Niagara system back to its origin.

    Shows the full inheritance chain from the given system up through
    any templates it was created from.

    asset_path: System to trace
    """
    escaped = _escape_py_string(asset_path)
    script = _LINEAGE_SCRIPT.format(asset_path=escaped)

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    lineage = data.get("lineage", [])
    lines = [
        f"Effect Lineage: {data.get('asset_path', asset_path)}",
        f"Chain depth: {data.get('depth', len(lineage))}",
        "",
    ]
    for i, step in enumerate(lineage):
        indent = "  " * i
        marker = "(current)" if i == 0 else "(template)"
        lines.append(f"  {indent}{step} {marker}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# find_parameter_conflicts
# ---------------------------------------------------------------------------

_PARAM_CONFLICTS_SCRIPT = '''\
import unreal, json
registry = unreal.AssetRegistryHelpers.get_asset_registry()
filt = unreal.ARFilter()
try:
    filt.class_paths = [unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraSystem")]
except Exception:
    filt.class_names = ["NiagaraSystem"]
{folder_filter}
assets = registry.get_assets(filt)

param_map = {{}}
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
            p_list = user_params.get_editor_property("parameters")
            if p_list:
                for p in p_list:
                    name = str(p.get_editor_property("name"))
                    try:
                        ptype = str(type(p).__name__)
                    except Exception:
                        ptype = "Unknown"
                    if name not in param_map:
                        param_map[name] = []
                    param_map[name].append({{"system": path, "type": ptype}})
    except Exception:
        pass

conflicts = []
for name, entries in param_map.items():
    types = set(e["type"] for e in entries)
    if len(types) > 1:
        conflicts.append({{"name": name, "entries": entries, "types": list(types)}})

print(json.dumps({{"total_params_checked": len(param_map), "conflicts": conflicts}}))
'''


@mcp.tool()
def find_parameter_conflicts(folder: str = "") -> str:
    """Find user parameters with the same name but different types across systems.

    Scans all Niagara systems and identifies naming conflicts where the
    same parameter name resolves to different types.

    folder: Optional folder to restrict scan
    """
    folder_filter = ""
    if folder:
        escaped_folder = _escape_py_string(folder)
        folder_filter = f'filt.package_paths = [unreal.Name("{escaped_folder}")]'
    script = _PARAM_CONFLICTS_SCRIPT.format(folder_filter=folder_filter)

    try:
        data = _run_bridge_script(script)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"

    err = _format_error(data)
    if err:
        return err

    conflicts = data.get("conflicts", [])
    total = data.get("total_params_checked", 0)

    if not conflicts:
        return f"No parameter conflicts found. Checked {total} unique parameter names."

    lines = [
        f"Parameter Conflicts",
        f"Unique parameters checked: {total}",
        f"Conflicts found: {len(conflicts)}",
        "",
    ]
    for c in conflicts:
        lines.append(f"  Parameter: '{c['name']}'")
        lines.append(f"  Types: {', '.join(c.get('types', []))}")
        for entry in c.get("entries", []):
            lines.append(f"    - {entry['system']} ({entry['type']})")
        lines.append("")

    return "\n".join(lines).rstrip()
