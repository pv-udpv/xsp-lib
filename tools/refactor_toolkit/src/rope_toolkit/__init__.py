"""Rope++ Refactor Toolkit.

Advanced Python code analysis & refactoring engine with tree-sitter indexing,
code graphs, and MCP/LSP integration.
"""

__version__ = "0.1.0-experimental"

from .engine import RopeEngine

__all__ = ["RopeEngine", "__version__"]
