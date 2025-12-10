"""Base storage backend class."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from ..config import RopeToolkitConfig


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    def __init__(self, config: RopeToolkitConfig) -> None:
        """Initialize storage backend.
        
        Args:
            config: Rope toolkit configuration
        """
        self.config = config
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize storage. Create schema if needed."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown storage gracefully."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if storage is healthy.
        
        Returns:
            True if healthy
        """
        pass
