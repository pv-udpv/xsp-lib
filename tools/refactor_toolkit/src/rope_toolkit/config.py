"""Configuration management."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional


@dataclass
class RopeToolkitConfig:
    """Configuration for rope toolkit."""
    project_root: Path
    cache_dir: Path = field(default_factory=lambda: Path('.rope_cache'))
    
    # Indexing options
    max_workers: int = 4
    incremental: bool = True
    
    # Storage options
    storage_backend: str = "sqlite"  # "sqlite", "postgresql", "duckdb"
    enable_vector_search: bool = True
    enable_graph_store: bool = False  # Neo4j/Kuzu
    
    # Feature flags
    enable_semantic_linking: bool = True
    enable_git_context: bool = True
    enable_lsp: bool = False
    enable_mcp: bool = False
    
    # Thresholds
    complexity_threshold: float = 8.0
    coupling_threshold: int = 10
    call_depth_threshold: int = 5
    
    # Extra
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate configuration."""
        self.project_root = self.project_root.resolve()
        self.cache_dir = self.cache_dir.resolve()
        
        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {self.project_root}")
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
