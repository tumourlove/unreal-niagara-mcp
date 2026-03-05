# unreal-niagara-mcp

Niagara particle system MCP server for Unreal Engine AI development. Provides 70 tools for inspecting, editing, creating, and procedurally generating Niagara VFX systems.

## Architecture

- **Python MCP server** (FastMCP, `mcp>=1.0.0`) — 70 tools across 8 modules
- **C++ plugin** (`NiagaraMCPBridge/`) — 39 `UFUNCTION(BlueprintCallable)` functions in 7 library classes
- **Editor bridge** — UDP multicast discovery (239.0.0.1:6766) → TCP commands (127.0.0.1:6776)

## Project Structure

```
src/unreal_niagara_mcp/
  server.py              — FastMCP app, _call_plugin(), _get_bridge(), _reset_state()
  editor_bridge.py       — UDP/TCP bridge to Unreal Editor
  config.py              — Environment variable configuration
  inspection/            — 16 read-only inspection tools (Python scripts via bridge)
  search/                — 8 search/discovery tools
  editing/               — 20 editing tools (C++ plugin calls)
  creation/              — 8 creation tools + preset recipes
  procedural/            — 10 procedural generation tools (HLSL, curves, distributions)
  analysis/              — 8 analysis/audit tools
NiagaraMCPBridge/        — UE C++ plugin (7 library classes)
tests/                   — 241 mock-based tests
```

## Conventions

- TDD: write tests first, mock the editor bridge, no live editor required
- Mock-based tests: all tests use `unittest.mock` to simulate editor responses
- Human-readable output: tools return formatted strings, not raw JSON
- No auto-save: tools dirty the asset but never save; the user decides when to save
- FastMCP with lazy bridge singleton and `_reset_state()` for test teardown
- Python UPROPERTY reads for inspection, C++ plugin calls for editing
- `uv` for package management, `pytest` for tests
- C++ plugin: `UFUNCTION(BlueprintCallable)` on `UBlueprintFunctionLibrary` subclasses
- All C++ editing inside `GEditor->BeginTransaction`/`EndTransaction` for Ctrl+Z undo
- Split C++ library classes by domain (not monolithic)

## Key Patterns

### Tool implementation
```python
@mcp.tool()
def my_tool(asset_path: str, ...) -> str:
    try:
        data = _call_plugin("LibraryName", "FunctionName", Param=value)
    except EditorNotRunning as e:
        return f"Editor not available: {e}"
    err = _format_error(data)
    if err:
        return err
    return "Formatted\n  result\n  here"
```

### Test pattern
```python
def test_my_tool(self):
    from unreal_niagara_mcp.module.tool_file import my_tool
    mock_data = {"key": "value"}
    with patch("unreal_niagara_mcp.module.tool_file._call_plugin", return_value=mock_data):
        result = my_tool("/Game/VFX/NS_Test")
    assert "expected" in result
```

## Running Tests

```bash
uv run pytest tests/ -v          # all 241 tests
uv run pytest tests/test_creation.py -v  # specific module
```
