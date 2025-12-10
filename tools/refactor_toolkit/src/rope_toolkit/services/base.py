"""Base service class."""

from abc import ABC, abstractmethod
from typing import Any

from ..config import RopeToolkitConfig


class ServiceBase(ABC):
    """Abstract base class for all services."""
    
    def __init__(self, config: RopeToolkitConfig) -> None:
        """Initialize service.
        
        Args:
            config: Rope toolkit configuration
        """
        self.config = config
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize service. Called once at startup."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown service. Called at teardown."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if service is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
