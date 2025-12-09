"""File-based transport for testing."""

import asyncio
from pathlib import Path

from xsp.core.transport import TransportType


class FileTransport:
    """Local filesystem transport for testing and fixtures."""

    @property
    def transport_type(self) -> TransportType:
        """Return transport type."""
        return TransportType.FILE

    async def send(
        self,
        endpoint: str,
        payload: bytes | None = None,
        metadata: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """
        Read file from filesystem.

        Args:
            endpoint: File path to read
            payload: Ignored
            metadata: Ignored
            timeout: Ignored

        Returns:
            File contents as bytes
        """
        path = Path(endpoint)
        return await asyncio.to_thread(path.read_bytes)

    async def close(self) -> None:
        """No-op for file transport."""
        pass
