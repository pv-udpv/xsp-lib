"""Protocol handler abstractions for xsp-lib."""

from typing import Any, Protocol, TypeVar

from xsp.core.types import Context, Headers, Params

T = TypeVar("T")


class AdRequest:
    """
    Universal ad request across all protocols.

    Generic request structure that can be mapped to protocol-specific
    parameters (VAST query params, OpenRTB BidRequest, etc.).
    """

    def __init__(
        self,
        *,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        url: str | None = None,
        placement_id: str | None = None,
        protocol: str | None = None,
        params: Params | None = None,
        context: Context | None = None,
        headers: Headers | None = None,
    ) -> None:
        """
        Initialize ad request.

        Args:
            user_id: User identifier
            ip_address: Client IP address
            user_agent: User agent string
            url: Content URL
            placement_id: Placement/slot identifier
            protocol: Requested protocol (vast, openrtb, etc.)
            params: Additional protocol-specific parameters
            context: Context data (e.g., macro substitution values)
            headers: HTTP headers
        """
        self.user_id = user_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.url = url
        self.placement_id = placement_id
        self.protocol = protocol
        self.params = params or {}
        self.context = context or {}
        self.headers = headers or {}


class AdResponse:
    """
    Universal ad response across all protocols.

    Generic response structure containing protocol-specific data
    and metadata about the response.
    """

    def __init__(
        self,
        *,
        protocol: str,
        data: str | dict[str, Any],
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize ad response.

        Args:
            protocol: Protocol used (vast, openrtb, etc.)
            data: Protocol-specific response data (XML string, JSON dict, etc.)
            status: Response status (success, error, timeout, etc.)
            error: Error message if status is error
            metadata: Additional response metadata
        """
        self.protocol = protocol
        self.data = data
        self.status = status
        self.error = error
        self.metadata = metadata or {}


class ProtocolHandler(Protocol):
    """
    Protocol handler interface.

    Each protocol (VAST, OpenRTB, DAAST) implements this interface
    to handle requests in a protocol-specific manner.
    """

    @property
    def protocol_name(self) -> str:
        """Return the protocol name (vast, openrtb, daast, etc.)."""
        ...

    async def handle(self, request: AdRequest) -> AdResponse:
        """
        Handle an ad request.

        Args:
            request: Universal ad request

        Returns:
            Universal ad response with protocol-specific data
        """
        ...

    async def close(self) -> None:
        """Release resources."""
        ...
