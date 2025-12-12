"""In-memory transport for testing."""

from xsp.core.transport import TransportType


class MemoryTransport:
    """In-memory transport for unit testing."""

    def __init__(self, response: bytes):
        """
        Initialize memory transport.

        Args:
            response: Bytes to return on send()
        """
        self.response = response

    @property
    def transport_type(self) -> TransportType:
        """Return transport type."""
        return TransportType.MEMORY

    async def request(
        self,
        endpoint: str,
        payload: bytes | None = None,
        metadata: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """
        Return stored response.

        All arguments are ignored.

        Returns:
            Stored response bytes
        """
        return self.response

    async def close(self) -> None:
        """No-op for memory transport."""
        pass
