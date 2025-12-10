"""Base upstream implementation."""

import asyncio
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from xsp.core.exceptions import DecodeError, TransportError, UpstreamTimeoutError
from xsp.core.transport import Transport

T = TypeVar("T")


class BaseUpstream(Generic[T]):
    """
    Base upstream implementation.

    Composes:
    - Transport layer for I/O
    - Decoder for response deserialization
    - Optional encoder for request serialization
    """

    def __init__(
        self,
        transport: Transport,
        decoder: Callable[[bytes], T],
        *,
        encoder: Callable[[Any], bytes] | None = None,
        endpoint: str = "",
        default_params: dict[str, Any] | None = None,
        default_headers: dict[str, str] | None = None,
        default_timeout: float = 30.0,
    ):
        """
        Initialize base upstream.

        Args:
            transport: Transport implementation for I/O
            decoder: Function to decode response bytes to type T
            encoder: Optional function to encode request data to bytes
            endpoint: Default endpoint/URL
            default_params: Default query parameters
            default_headers: Default headers
            default_timeout: Default timeout in seconds
        """
        self.transport = transport
        self.decoder = decoder
        self.encoder = encoder
        self.endpoint = endpoint
        self.default_params = default_params or {}
        self.default_headers = default_headers or {}
        self.default_timeout = default_timeout

    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
        payload: Any = None,
        endpoint: str | None = None,
        **kwargs: Any,
    ) -> T:
        """
        Fetch data from upstream.

        Args:
            params: Query parameters (merged with defaults)
            headers: HTTP headers (merged with defaults)
            context: Additional context data (unused in base implementation)
            timeout: Request timeout in seconds
            payload: Optional request payload (will be encoded if encoder provided)
            endpoint: Override default endpoint
            **kwargs: Additional transport-specific arguments

        Returns:
            Decoded response of type T

        Raises:
            UpstreamTimeoutError: If request times out
            TransportError: If transport operation fails
            DecodeError: If response decoding fails
        """
        # Merge parameters
        merged_params = {**self.default_params, **(params or {})}
        merged_headers = {**self.default_headers, **(headers or {})}
        effective_timeout = timeout if timeout is not None else self.default_timeout
        effective_endpoint = endpoint or self.endpoint

        # Encode payload if provided
        encoded_payload: bytes | None = None
        if payload is not None:
            if self.encoder is None:
                raise ValueError("Encoder not provided but payload specified")
            encoded_payload = self.encoder(payload)

        # Prepare metadata (headers)
        metadata = merged_headers.copy()

        # Add params to metadata if supported
        if merged_params:
            import json

            metadata["_params"] = json.dumps(merged_params)

        # Send request with timeout
        try:
            raw_response = await asyncio.wait_for(
                self.transport.send(
                    endpoint=effective_endpoint,
                    payload=encoded_payload,
                    metadata=metadata,
                    timeout=effective_timeout,
                ),
                timeout=effective_timeout,
            )
        except TimeoutError as e:
            raise UpstreamTimeoutError(f"Request timed out after {effective_timeout}s") from e
        except Exception as e:
            raise TransportError(f"Transport error: {e}") from e

        # Decode response
        try:
            return self.decoder(raw_response)
        except Exception as e:
            raise DecodeError(f"Failed to decode response: {e}") from e

    async def close(self) -> None:
        """Close transport and release resources."""
        await self.transport.close()

    async def health_check(self) -> bool:
        """
        Check upstream health.

        Returns:
            True if upstream is healthy, False otherwise
        """
        try:
            # Try a simple fetch with minimal timeout
            await self.fetch(timeout=5.0)
            return True
        except Exception:
            return False
