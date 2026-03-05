# unreal-niagara-mcp

Niagara particle system MCP server for Unreal Engine AI development. Provides 69 tools for inspecting, editing, creating, and procedurally generating Niagara VFX systems.

## Design Doc

`C:\Projects\MCP_Ideas\docs\plans\2026-03-05-niagara-mcp-design.md`

## Conventions

- TDD: write tests first, mock the editor bridge, no live editor required
- Mock-based tests: all tests use unittest.mock to simulate editor responses
- Human-readable output: tools return formatted strings, not raw JSON
- No auto-save: tools dirty the asset but never save; the user decides when to save
- FastMCP with lazy bridge singleton and `_reset_state()` for test teardown
- Python UPROPERTY reads for inspection, C++ plugin calls for editing
- `uv` for package management
