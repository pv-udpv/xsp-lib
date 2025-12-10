"""Main RopeEngine — orchestrator of all services."""

from typing import Optional, List, Dict, Any
from pathlib import Path

from .config import RopeToolkitConfig
from .types import HealthReport, RefactoringPlan, RefactoringActionType
from .services import (
    CodebaseIndexerService,
    CodeGraphService,
    MetricsService,
    ObservationService,
    RelationshipService,
)
from .storage import SQLiteStore


class RopeEngine:
    """Main orchestrator for rope toolkit.
    
    Coordinates all services and backends:
    - Indexing (tree-sitter)
    - Analysis (metrics, observations)
    - Graph management
    - Refactoring planning
    - Storage persistence
    """
    
    def __init__(self, project_root: str | Path) -> None:
        """Initialize RopeEngine.
        
        Args:
            project_root: Root directory of project to analyze
        """
        self.config = RopeToolkitConfig(project_root=Path(project_root))
        
        # Initialize services
        self.indexer = CodebaseIndexerService(self.config)
        self.graph = CodeGraphService(self.config)
        self.metrics = MetricsService(self.config)
        self.observations = ObservationService(self.config)
        self.relationships = RelationshipService(self.config)
        
        # Initialize storage
        self.storage = SQLiteStore(self.config)
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all services and storage."""
        await self.indexer.initialize()
        await self.graph.initialize()
        await self.metrics.initialize()
        await self.observations.initialize()
        await self.relationships.initialize()
        await self.storage.initialize()
        self._initialized = True
    
    async def shutdown(self) -> None:
        """Shutdown all services and storage."""
        await self.indexer.shutdown()
        await self.graph.shutdown()
        await self.metrics.shutdown()
        await self.observations.shutdown()
        await self.relationships.shutdown()
        await self.storage.shutdown()
        self._initialized = False
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all services.
        
        Returns:
            Dictionary of service health status
        """
        return {
            "indexer": self.indexer.health_check(),
            "graph": self.graph.health_check(),
            "metrics": self.metrics.health_check(),
            "observations": self.observations.health_check(),
            "relationships": self.relationships.health_check(),
            "storage": self.storage.health_check(),
        }
    
    async def index_project(self) -> int:
        """Index entire project.
        
        Returns:
            Number of symbols indexed
        """
        if not self._initialized:
            await self.initialize()
        return await self.indexer.index_project()
    
    async def analyze(self) -> HealthReport:
        """Perform full codebase analysis.
        
        Returns:
            Health report with score and observations
        """
        if not self._initialized:
            await self.initialize()
        
        # TODO: Implement full analysis
        return HealthReport(health_score=0.0, total_symbols=0)
    
    def plan_rename(self, old_name: str, new_name: str) -> RefactoringPlan:
        """Plan a rename refactoring.
        
        Args:
            old_name: Current name
            new_name: New name
            
        Returns:
            Refactoring plan with preview
        """
        # TODO: Implement rename planning
        return RefactoringPlan(
            operation=RefactoringActionType.RENAME,
            target_symbol=old_name,
        )
    
    def what_breaks_if(self, symbol: str) -> Dict[str, Any]:
        """Analyze impact of changing a symbol.
        
        Args:
            symbol: Symbol identifier
            
        Returns:
            Impact analysis report
        """
        # TODO: Implement impact analysis
        return {"references": [], "files_affected": []}
