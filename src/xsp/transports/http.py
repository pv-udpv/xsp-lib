"""HTTP/HTTPS transport implementation."""

from typing import Any

import httpx

from xsp.core.exceptions import (
    TransportConnectionError,
    TransportError,
    TransportTimeoutError,
)
from xsp.core.transport import TransportType


class HttpTransport:
    """HTTP/HTTPS transport for REST APIs."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        method: str = "GET",
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
        timeout: float = 30.0,
        follow_redirects: bool = True,
        verify_ssl: bool = True,
    ):
        """
        Initialize HTTP transport.

        Args:
            client: Optional httpx.AsyncClient instance
            method: HTTP method (GET, POST, etc.)
            max_connections: Maximum number of connections in pool
            max_keepalive_connections: Maximum number of keepalive connections
            keepalive_expiry: Time in seconds before keepalive connections expire
            timeout: Default request timeout in seconds
            follow_redirects: Whether to follow redirects
            verify_ssl: Whether to verify SSL certificates

        Raises:
            ImportError: If httpx is not installed
        """
        if client is None:
            limits = httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
                keepalive_expiry=keepalive_expiry,
            )
            self.client = httpx.AsyncClient(
                limits=limits,
                follow_redirects=follow_redirects,
                verify=verify_ssl,
            )
        else:
            self.client = client

        self.method = method.upper()
        self.default_timeout = timeout
        self._owns_client = client is None

    @property
    def transport_type(self) -> TransportType:
        """Return transport type."""
        return TransportType.HTTP

    async def send(
        self,
        endpoint: str,
        payload: bytes | None = None,
        metadata: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """
        Send HTTP request.

        Args:
            endpoint: URL to request
            payload: Optional request body
            metadata: Headers and parameters (params in "_params" key)
            timeout: Request timeout

        Returns:
            Response body as bytes
        """
        headers = metadata.copy() if metadata else {}

        # Extract params from metadata
        params = None
        if "_params" in headers:
            import json

            params_str = headers.pop("_params")
            try:
                params = json.loads(params_str)
            except json.JSONDecodeError:
                params = {}

        # Build request arguments
        request_args: dict[str, Any] = {
            "method": self.method,
            "url": endpoint,
            "headers": headers,
        }

        if params:
            request_args["params"] = params

        if payload is not None:
            request_args["content"] = payload

        if timeout is not None:
            request_args["timeout"] = timeout
        else:
            request_args["timeout"] = self.default_timeout

        # Send request with error handling
        try:
            response = await self.client.request(**request_args)
            response.raise_for_status()
        except httpx.TimeoutException as e:
            raise TransportTimeoutError(f"Request timed out: {endpoint}") from e
        except (httpx.ConnectError, httpx.NetworkError) as e:
            raise TransportConnectionError(f"Connection failed: {endpoint}") from e
        except httpx.HTTPStatusError as e:
            raise TransportError(
                f"HTTP error {e.response.status_code}: {endpoint}",
                status_code=e.response.status_code,
            ) from e
        except Exception as e:
            raise TransportError(f"Transport error: {endpoint}") from e

        return response.content

    async def close(self) -> None:
        """Close HTTP client if owned."""
        if self._owns_client:
            await self.client.aclose()
