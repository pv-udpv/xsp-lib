"""Protocol handler interface for protocol-agnostic orchestration."""

from abc import ABC, abstractmethod

from xsp.orchestrator.schemas import AdRequest, AdResponse


class ProtocolHandler(ABC):
    """
    Abstract protocol handler interface.

    Each protocol (VAST, VMAP, OpenRTB, custom) implements this interface
    to provide protocol-specific ad fetching and tracking logic.

    The orchestrator delegates to protocol handlers for actual protocol
    operations while handling cross-cutting concerns like caching and metrics.

    Examples:
        VAST protocol handler:
            class VastProtocolHandler(ProtocolHandler):
                async def fetch(self, request: AdRequest, **context) -> AdResponse:
                    # Map AdRequest to VAST parameters
                    # Fetch VAST XML
                    # Parse response
                    # Map to AdResponse
                    pass

        OpenRTB protocol handler:
            class OpenRTBProtocolHandler(ProtocolHandler):
                async def fetch(self, request: AdRequest, **context) -> AdResponse:
                    # Map AdRequest to OpenRTB bid request
                    # Send bid request
                    # Parse bid response
                    # Map to AdResponse
                    pass
    """

    @abstractmethod
    async def fetch(
        self,
        request: AdRequest,
        **context: object,
    ) -> AdResponse:
        """
        Fetch ad using protocol-specific logic.

        Maps the generic AdRequest to protocol-specific parameters,
        executes the protocol fetch operation, and maps the protocol
        response back to AdResponse.

        Args:
            request: Normalized protocol-agnostic ad request
            **context: Additional context (config, cache, state, etc.)

        Returns:
            Normalized protocol-agnostic ad response

        Raises:
            UpstreamError: If ad fetch fails
            ValidationError: If request validation fails
        """
        ...

    @abstractmethod
    async def track(
        self,
        event: str,
        response: AdResponse,
        **context: object,
    ) -> None:
        """
        Track event for delivered ad.

        Fires tracking URLs or performs protocol-specific tracking
        operations for ad events (impression, click, complete, etc.).

        Args:
            event: Event type ('impression', 'click', 'complete', 'error', etc.)
            response: Ad response from fetch() containing tracking URLs
            **context: Additional context

        Raises:
            UpstreamError: If tracking fails
        """
        ...

    @abstractmethod
    def validate_request(self, request: AdRequest) -> bool:
        """
        Validate that request has required fields for this protocol.

        Checks that the AdRequest contains all required fields for the
        specific protocol implementation.

        Args:
            request: Ad request to validate

        Returns:
            True if request is valid for this protocol, False otherwise

        Examples:
            VAST handler:
                def validate_request(self, request: AdRequest) -> bool:
                    return "slot_id" in request and "user_id" in request

            OpenRTB handler:
                def validate_request(self, request: AdRequest) -> bool:
                    return (
                        "slot_id" in request
                        and "user_id" in request
                        and "player_size" in request
                    )
        """
        ...
