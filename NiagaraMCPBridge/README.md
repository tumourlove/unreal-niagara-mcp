# NiagaraMCPBridge

C++ Unreal Engine editor plugin that provides Blueprint-callable wrappers for Niagara editing APIs, enabling AI-assisted VFX authoring via Python scripting.

Gives AI assistants full read/write access to Niagara internals — system creation, emitter management, module stack editing, parameter binding, renderer configuration, data interface setup, HLSL expression management, and atomic batch operations — through 39 `UFUNCTION`s callable from the editor's Python environment.

## Why?

`UNiagaraSystem` and `UNiagaraEmitter` have zero `UFUNCTION`-tagged methods — all APIs are `NIAGARA_API` C++ only. Python can read properties via reflection, but editing operations (adding emitters, inserting modules, binding parameters, configuring renderers) are impossible without C++ access. This plugin is not a convenience layer but the backbone of all Niagara editing operations.

**Companion MCP server:** [unreal-niagara-mcp](https://github.com/tumourlove/unreal-niagara-mcp) wraps these functions as MCP tools for AI assistants (70 tools total).

**Complements** (does not replace):
- [unreal-source-mcp](https://github.com/tumourlove/unreal-source-mcp) — Engine-level source intelligence (full UE C++ and HLSL)
- [unreal-project-mcp](https://github.com/tumourlove/unreal-project-mcp) — Project-level source intelligence (your C++ code)
- [unreal-editor-mcp](https://github.com/tumourlove/unreal-editor-mcp) — Build diagnostics and editor log tools (Live Coding, error parsing, log search)
- [unreal-blueprint-mcp](https://github.com/tumourlove/unreal-blueprint-mcp) — Blueprint graph reading (nodes, pins, connections, execution flow)
- [unreal-blueprint-reader](https://github.com/tumourlove/unreal-blueprint-reader) — C++ editor plugin that serializes Blueprint graphs to JSON for AI tooling
- [unreal-material-mcp](https://github.com/tumourlove/unreal-material-mcp) — Material graph intelligence, editing, and procedural creation (46 tools: expressions, parameters, instances, graph building, templates, C++ plugin)
- [unreal-config-mcp](https://github.com/tumourlove/unreal-config-mcp) — Config/INI intelligence (resolve inheritance chains, search settings, diff from defaults, explain CVars)
- [unreal-animation-mcp](https://github.com/tumourlove/unreal-animation-mcp) — Animation data inspector and editor (sequences, montages, blend spaces, ABPs, skeletons, 62 tools)
- [unreal-api-mcp](https://github.com/nicobailon/unreal-api-mcp) by [Nico Bailon](https://github.com/nicobailon) — API surface lookup (signatures, #include paths, deprecation warnings)

Together these servers give AI agents full-stack UE understanding: engine internals, API surface, your project code, build/runtime feedback, Blueprint graph data, config/INI intelligence, material graph inspection + editing, animation data inspection + editing, and Niagara VFX inspection + creation.

## Installation

Copy or symlink this plugin to your project's `Plugins/` folder:

```
MyProject/
  Plugins/
    NiagaraMCPBridge/
      NiagaraMCPBridge.uplugin
      Source/
        NiagaraMCPBridge/
          ...
```

Recompile the project or restart the editor. Requires the **Niagara** plugin to be enabled.

## Prerequisites

- **Unreal Engine 5.x** (tested on 5.7)
- **Niagara plugin** enabled (enabled by default in most projects)
- **Python Remote Execution** enabled in Project Settings (for AI tooling access)

## Library Classes (7)

The plugin is split into 7 domain-specific `UBlueprintFunctionLibrary` subclasses with 39 functions total.

### NiagaraSystemLibrary (8 functions)

| Function | Description |
|----------|-------------|
| `AddEmitter` | Add an emitter to a system from a template asset |
| `RemoveEmitter` | Remove an emitter by handle ID or name |
| `DuplicateEmitter` | Duplicate an emitter within a system |
| `SetEmitterEnabled` | Enable or disable an emitter |
| `ReorderEmitters` | Reorder emitters within a system |
| `SetEmitterProperty` | Set a property on an emitter by name (JSON value) |
| `RequestCompile` | Request recompilation of a Niagara system |
| `CreateNiagaraSystem` | Create a new system, optionally from a template |

### NiagaraModuleLibrary (12 functions)

| Function | Description |
|----------|-------------|
| `AddModule` | Add a module to an emitter's stack at a specific position |
| `RemoveModule` | Remove a module from an emitter's stack |
| `ReorderModules` | Reorder modules within a stack |
| `SetModuleEnabled` | Enable or disable a module |
| `SetModuleInput` | Set a module input value (float, vector, bool, etc.) |
| `GetModuleInputs` | Get all inputs for a module with current values |
| `CreateNiagaraModule` | Create a module script from HLSL or auto-generated code |
| `CreateNiagaraFunction` | Create a function script from HLSL code |
| `AddSimulationStage` | Add a simulation stage to an emitter |
| `RemoveSimulationStage` | Remove a simulation stage |
| `SetSimulationStageProperty` | Set a simulation stage property |
| `GetSimulationStages` | Get simulation stage configuration |

### NiagaraParameterLibrary (9 functions)

| Function | Description |
|----------|-------------|
| `AddUserParameter` | Add a user parameter to the system |
| `RemoveUserParameter` | Remove a user parameter |
| `SetUserParameterDefault` | Set a user parameter's default value |
| `BindParameter` | Bind a parameter to a source |
| `UnbindParameter` | Remove a parameter binding |
| `SetSystemProperty` | Set a system-level property |
| `GetParameterBindings` | Get all parameter bindings for a system |
| `SetScalability` | Configure scalability settings |
| `GetScalabilitySettings` | Get current scalability configuration |

### NiagaraRendererLibrary (6 functions)

| Function | Description |
|----------|-------------|
| `AddRenderer` | Add a renderer to an emitter (sprite, mesh, ribbon, etc.) |
| `RemoveRenderer` | Remove a renderer from an emitter |
| `SetRendererProperty` | Set a renderer property (binding, mesh, etc.) |
| `SetRendererMaterial` | Assign a material to a renderer |
| `GetRendererProperties` | Get all properties of a renderer |
| `GetRendererList` | List all renderers on an emitter with types |

### NiagaraDILibrary (1 function)

| Function | Description |
|----------|-------------|
| `SetDataInterfaceProperty` | Configure a data interface property |

### NiagaraHLSLLibrary (1 function)

| Function | Description |
|----------|-------------|
| `SetCustomHLSL` | Set or update custom HLSL expressions on a module |

### NiagaraBatchLibrary (2 functions)

| Function | Description |
|----------|-------------|
| `BatchEdit` | Execute multiple edit operations atomically in a single transaction |
| `CloneEmitterBetweenSystems` | Clone an emitter from one system to another |

### Example (editor Python console)

```python
import unreal
result = unreal.NiagaraMCPSystemLibrary.add_emitter(
    '/Game/VFX/NS_Fire',
    '/Niagara/Emitters/SimpleSprite',
    'NewEmitter'
)
print(result)
```

## License

MIT
