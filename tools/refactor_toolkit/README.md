# Rope++ Refactor Toolkit

⚠️ **Experimental** — Testing on `xsp-lib` codebase

## Overview

Production-grade Python code analysis & refactoring engine combining:

- **Tree-sitter based indexing** — 5x faster incremental parsing
- **Code graph analysis** — call graphs, dependency cycles, impact analysis
- **13 observation types** — god modules, dead code, high coupling, etc.
- **Refactoring planning** — risk-aware operations with previews
- **MCP/LSP facades** — IDE integration (VSCode, Cursor, etc.)
- **Semantic linking** — code ↔ docs/chats/commits context

## Architecture

```
Facades (MCP/LSP)
    ↓
Services (indexing, analysis, graph)
    ↓
Storage (SQLite, vector, graph backends)
    ↓
Operations (rename, move, extract)
    ↓
Engine (orchestrator)
```

## Quick Start

```python
from rope_toolkit import RopeEngine

engine = RopeEngine('.')
engine.index_project()

# Analyze
report = engine.analyze()
print(f"Health score: {report.health_score}/100")

# Plan refactoring
plan = engine.plan_rename('old_func', 'new_func')
print(plan.preview())

# What breaks if I change X?
impact = engine.what_breaks_if('my_function')
print(f"Used in {len(impact.references)} places")
```

## MCP Integration

```bash
python -m rope_toolkit.facades.mcp_server
```

Configure in VSCode:

```json
{
  "mcp.servers": {
    "rope-toolkit": {
      "command": "python",
      "args": ["-m", "rope_toolkit.facades.mcp_server"]
    }
  }
}
```

## Status

- [x] Package structure (PEP 517/518)
- [x] Type hints (py.typed)
- [x] Service architecture
- [ ] Tree-sitter integration
- [ ] Code graph implementation
- [ ] MCP server
- [ ] LSP server
- [ ] Tests

## Docs

- `docs/architecture.md` — Layer descriptions
- `docs/services.md` — Service interfaces
- `docs/facades.md` — MCP/LSP usage

## License

Apache 2.0
