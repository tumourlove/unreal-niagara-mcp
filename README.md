# unreal-niagara-mcp

Niagara particle system intelligence for Unreal Engine AI development via [Model Context Protocol](https://modelcontextprotocol.io/).

Gives AI assistants full read/write access to Niagara VFX systems — inspect emitters, edit module stacks, create systems from presets, generate HLSL modules, produce procedural particle distributions, and analyze effect performance. 70 tools, 39 C++ plugin functions, 241 tests.

## Why?

Niagara systems are complex multi-layered assets — emitters with module stacks, parameter stores, data interfaces, simulation stages, renderers, and events — all opaque to AI. The AI cannot inspect, search, edit, or create VFX programmatically without this server.

Procedural VFX authoring (HLSL generation, mathematical curves, multi-emitter coordination, effect variations) is where AI has its biggest edge over manual workflows. This server makes that possible.

**Complements** (does not replace):
- [unreal-source-mcp](https://github.com/tumourlove/unreal-source-mcp) — Engine-level source intelligence (full UE C++ and HLSL)
- [unreal-material-mcp](https://github.com/tumourlove/unreal-material-mcp) — Material graph intelligence (nodes, parameters, textures)
- [unreal-blueprint-mcp](https://github.com/tumourlove/unreal-blueprint-mcp) — Blueprint graph reading (nodes, pins, connections)
- [unreal-config-mcp](https://github.com/tumourlove/unreal-config-mcp) — Config/INI intelligence (settings, CVars, inheritance)

## Quick Start

### Install from GitHub

```bash
uvx --from git+https://github.com/tumourlove/unreal-niagara-mcp.git unreal-niagara-mcp
```

### Claude Code Configuration

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "unreal-niagara": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/tumourlove/unreal-niagara-mcp.git", "unreal-niagara-mcp"],
      "env": {
        "UE_PROJECT_PATH": "D:/Unreal Projects/MyProject"
      }
    }
  }
}
```

Or run from local source during development:

```json
{
  "mcpServers": {
    "unreal-niagara": {
      "command": "uv",
      "args": ["run", "--directory", "C:/Projects/unreal-niagara-mcp", "unreal-niagara-mcp"],
      "env": {
        "UE_PROJECT_PATH": "D:/Unreal Projects/MyProject"
      }
    }
  }
}
```

### C++ Plugin Installation

The server requires the `NiagaraMCPBridge` C++ plugin for all editing operations.

1. Copy the `NiagaraMCPBridge/` folder into your project's `Plugins/` directory
2. Regenerate project files and build
3. Enable the plugin in the editor (Edit → Plugins → search "NiagaraMCPBridge")

The plugin provides 39 `UFUNCTION(BlueprintCallable)` functions across 7 library classes:
- `NiagaraSystemLibrary` — System creation, emitter management, compilation
- `NiagaraModuleLibrary` — Module stack editing, HLSL script creation
- `NiagaraParameterLibrary` — Parameter binding, user parameters, defaults
- `NiagaraRendererLibrary` — Renderer management, material assignment
- `NiagaraDILibrary` — Data interface configuration
- `NiagaraHLSLLibrary` — Custom HLSL expression management
- `NiagaraBatchLibrary` — Atomic multi-step batch operations

## Tools (70)

### Inspection (16 tools)

| Tool | Description |
|------|-------------|
| `get_niagara_system_info` | Full system overview — emitter count, user parameters, compile status |
| `get_niagara_emitters` | List all emitters with sim target, renderer type, module counts |
| `get_emitter_summary` | Detailed emitter breakdown — modules, renderers, events, DI |
| `get_niagara_modules` | Module stack for an emitter with inputs and enabled state |
| `get_module_inputs` | All inputs for a specific module with current values |
| `get_module_graph` | Module's internal node graph structure |
| `get_niagara_parameters` | All parameters in a system/emitter namespace |
| `get_niagara_user_parameters` | User-exposed parameters with types and defaults |
| `get_niagara_renderers` | Renderer details — type, material, mesh, ribbon settings |
| `get_niagara_events` | Event handlers and generators across emitters |
| `get_data_interfaces` | Data interfaces used by an emitter |
| `get_di_functions` | Functions available on a data interface type |
| `get_simulation_stages` | Simulation stage configuration and iteration sources |
| `get_niagara_stats` | Performance stats — particle counts, memory, GPU time estimates |
| `get_niagara_inventory` | Asset inventory — all Niagara assets in a directory tree |
| `get_hlsl_output` | Compiled HLSL output for a module or emitter script |

### Search & Discovery (8 tools)

| Tool | Description |
|------|-------------|
| `search_niagara_systems` | Find systems by name pattern across the project |
| `search_niagara_modules` | Find modules used across systems with usage counts |
| `search_by_parameter` | Find systems using a specific parameter name or type |
| `search_by_material` | Find systems referencing a specific material |
| `search_by_data_interface` | Find systems using a specific data interface class |
| `query_niagara` | Natural-language style queries across Niagara assets |
| `find_niagara_references` | Find all references to a Niagara asset |
| `find_similar_systems` | Find systems with similar structure to a reference |

### Editing (20 tools)

| Tool | Description |
|------|-------------|
| `add_module` | Add a module to an emitter's stack at a specific position |
| `remove_module` | Remove a module from an emitter's stack |
| `reorder_modules` | Reorder modules within a stack |
| `set_module_enabled` | Enable or disable a module |
| `set_module_input` | Set a module input value (float, vector, bool, etc.) |
| `add_emitter` | Add an emitter to a system from a template |
| `remove_emitter` | Remove an emitter from a system |
| `reorder_emitters` | Reorder emitters within a system |
| `set_emitter_enabled` | Enable or disable an emitter |
| `set_emitter_property` | Set an emitter property by name |
| `add_renderer` | Add a renderer to an emitter (sprite, mesh, ribbon, etc.) |
| `remove_renderer` | Remove a renderer from an emitter |
| `set_renderer_property` | Set a renderer property (binding, material, mesh) |
| `set_renderer_material` | Assign a material to a renderer |
| `add_user_parameter` | Add a user parameter to the system |
| `remove_user_parameter` | Remove a user parameter |
| `set_user_parameter_default` | Set a user parameter's default value |
| `set_system_property` | Set a system-level property |
| `set_scalability` | Configure scalability settings (distance, budget, cull) |
| `batch_edit_niagara` | Execute multiple edits atomically via batch JSON |

### Creation (8 tools)

| Tool | Description |
|------|-------------|
| `create_niagara_system` | Create a new system, optionally from a template |
| `create_niagara_emitter` | Create a standalone emitter asset (CPU or GPU) |
| `create_niagara_module` | Create a module script from HLSL or auto-generated code |
| `create_niagara_function` | Create a function script from HLSL code |
| `duplicate_niagara_system` | Duplicate an existing system to a new path |
| `duplicate_emitter` | Duplicate an emitter within a system |
| `clone_emitter_between_systems` | Clone an emitter from one system to another |
| `create_from_preset` | Create a system from a built-in preset recipe |

### Procedural Generation (10 tools)

| Tool | Description |
|------|-------------|
| `generate_module_hlsl` | Generate HLSL code for a module with proper conventions |
| `generate_dynamic_input_expression` | Generate HLSL expressions for dynamic inputs |
| `generate_curve_from_function` | Generate curve keys from mathematical functions |
| `create_particle_distribution` | Create spatial distributions (sphere, cone, grid, etc.) |
| `create_procedural_system` | Generate a complete system from a text description |
| `generate_effect_variations` | Create parameter variations of an existing effect |
| `create_sim_stage_setup` | Generate simulation stage configurations |
| `batch_update_niagara` | Apply procedural updates to multiple systems |
| `trace_effect_lineage` | Trace the creation/derivation history of an effect |
| `preview_particle_count` | Estimate particle counts for given spawn/lifetime settings |

### Analysis (8 tools)

| Tool | Description |
|------|-------------|
| `audit_niagara_system` | Full system audit — performance, best practices, warnings |
| `audit_pooling` | Check pooling configuration and recommend settings |
| `audit_scalability` | Validate scalability settings across quality levels |
| `compare_niagara_systems` | Side-by-side comparison of two systems |
| `find_parameter_conflicts` | Find conflicting parameter definitions across emitters |
| `validate_bindings` | Validate all parameter bindings are resolvable |
| `trace_parameter_bindings` | Trace how a parameter flows through the system |
| `get_module_usage_map` | Map which modules are used across all systems |

### Example Workflows

**Inspect a VFX system:**
> "Use `get_niagara_system_info` with `/Game/VFX/NS_Fire` to see the system overview, then `get_emitter_summary` for each emitter."

**Create a burst effect from a preset:**
> "Use `create_from_preset` with preset `burst_sprite` to create a ready-to-use burst particle system."

**Generate a custom force module:**
> "Use `create_niagara_module` with inputs `[{"name":"Strength","type":"float","default":"100.0"}]`, outputs `[{"name":"Force","type":"float3"}]`, and HLSL code to create a custom radial force module."

**Audit performance:**
> "Use `audit_niagara_system` on `/Game/VFX/NS_Explosion` to check for performance issues, then `audit_scalability` to verify distance culling."

**Create procedural variations:**
> "Use `generate_effect_variations` on `/Game/VFX/NS_Magic` to create 5 color/size variants for different spell types."

## Architecture

```
┌─────────────────────────────────────────────────┐
│  AI Assistant (Claude, etc.)                     │
│  ↕ MCP Protocol (stdio)                          │
├─────────────────────────────────────────────────┤
│  Python MCP Server (FastMCP)                     │
│  70 tools across 8 modules                       │
│  ↕ Editor Bridge (UDP multicast → TCP)           │
├─────────────────────────────────────────────────┤
│  Unreal Editor                                   │
│  ├── Python Scripts (inspection, search)          │
│  └── NiagaraMCPBridge C++ Plugin                  │
│      39 UFUNCTION(BlueprintCallable) functions    │
│      7 library classes                            │
│      GEditor→BeginTransaction for undo support    │
└─────────────────────────────────────────────────┘
```

**Why a C++ plugin?** `UNiagaraSystem` and `UNiagaraEmitter` have zero `UFUNCTION`-tagged methods — all APIs are `NIAGARA_API` C++ only. The plugin is not a convenience layer but the backbone of all editing operations.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `UE_PROJECT_PATH` | Yes | Path to the UE project root (containing the .uproject file) |
| `UE_EDITOR_PYTHON_PORT` | No | TCP port for editor Python bridge commands (default: `6776`) |
| `UE_MULTICAST_GROUP` | No | UDP multicast group for editor discovery (default: `239.0.0.1`) |
| `UE_MULTICAST_PORT` | No | UDP multicast port for editor discovery (default: `6766`) |
| `UE_MULTICAST_BIND` | No | Local interface to bind multicast listener (default: `127.0.0.1`) |

## Adding to Your Project's CLAUDE.md

```markdown
## Niagara VFX Intelligence (unreal-niagara MCP)

Use `unreal-niagara` MCP tools to inspect, edit, create, and analyze Niagara particle systems.

| Tool Category | When |
|---------------|------|
| `get_niagara_*` | Inspect system structure, emitters, modules, parameters |
| `search_niagara_*` | Find systems by name, parameter, material, or DI |
| `add/remove/set_*` | Edit module stacks, emitters, renderers, parameters |
| `create_niagara_*` | Create new systems, emitters, modules, functions |
| `create_from_preset` | Generate systems from built-in preset recipes |
| `generate_*` | HLSL code generation, curves, distributions |
| `audit_*` | Performance analysis, scalability, best practices |
| `batch_edit_niagara` | Atomic multi-step edit operations |
```

## Development

```bash
# Clone and install
git clone https://github.com/tumourlove/unreal-niagara-mcp.git
cd unreal-niagara-mcp
uv sync

# Run tests
uv run pytest tests/ -v

# Run server locally
uv run unreal-niagara-mcp
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Unreal Engine 5.x project with Niagara plugin enabled
- NiagaraMCPBridge C++ plugin (for editing operations)

## License

MIT
