"""Protocol handler abstraction for AdTech protocols."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

# Type variables for request and response types
TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")


class ProtocolHandler(ABC, Generic[TRequest, TResponse]):
    """
    Abstract base class for protocol-specific handlers.

    Protocol handlers implement the logic for specific AdTech protocols
    (VAST, OpenRTB, DAAST, etc.) and translate between protocol-agnostic
    requests and protocol-specific formats.

    Type Parameters:
        TRequest: Protocol-specific request type
        TResponse: Protocol-specific response type

    Example:
        >>> class VastHandler(ProtocolHandler[VastRequest, VastResponse]):
        ...     async def handle(self, request: VastRequest) -> VastResponse:
        ...         # Process VAST request and return response
        ...         pass
    """

    @abstractmethod
    async def handle(self, request: TRequest, **kwargs: Any) -> TResponse:
        """
        Handle a protocol-specific request.

        Args:
            request: Protocol-specific request object
            **kwargs: Additional protocol-specific arguments

        Returns:
            Protocol-specific response object

        Raises:
            ProtocolError: If protocol handling fails
            ValidationError: If request validation fails
        """
        ...

    async def close(self) -> None:
        """
        Release resources used by the protocol handler.

        Override this method if your handler needs cleanup.
        """
        pass

    async def health_check(self) -> bool:
        """
        Check handler health status.

        Returns:
            True if handler is healthy, False otherwise

        Override this method to implement health checks.
        """
        return True
