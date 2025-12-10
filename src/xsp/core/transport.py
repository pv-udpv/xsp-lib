"""Transport layer protocol."""

from enum import Enum
from typing import Protocol


class TransportType(str, Enum):
    """Supported transport types."""

    HTTP = "http"
    HTTPS = "https"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    FILE = "file"
    MEMORY = "memory"
    S3 = "s3"


class Transport(Protocol):
    """Transport layer protocol."""

    @property
    def transport_type(self) -> TransportType:
        """Return the transport type."""
        ...

    async def request(
        self,
        endpoint: str,
        payload: bytes | None = None,
        metadata: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Send a request and return the response."""
        ...

    async def close(self) -> None:
        """Close the transport and release resources."""
        ...
