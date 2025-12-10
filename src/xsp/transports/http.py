"""HTTP/HTTPS transport implementation."""

from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from xsp.core.transport import TransportType
from xsp.core.exceptions import (
    TransportError,
    TransportTimeoutError,
    TransportConnectionError,
)


class HttpTransport:
    """HTTP/HTTPS transport for REST APIs with connection pooling."""

    def __init__(
        self,
        client: Any | None = None,
        method: str = "GET",
        *,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
        timeout: float = 30.0,
        follow_redirects: bool = True,
        verify_ssl: bool = True,
    ):
        """
        Initialize HTTP transport with connection pooling.

        Args:
            client: Optional httpx.AsyncClient instance (if provided, pool settings ignored)
            method: Default HTTP method (GET, POST, etc.)
            max_connections: Maximum number of concurrent connections
            max_keepalive_connections: Maximum number of idle connections to keep
            keepalive_expiry: Time in seconds to keep idle connections alive
            timeout: Default request timeout in seconds
            follow_redirects: Whether to follow HTTP redirects
            verify_ssl: Whether to verify SSL certificates

        Raises:
            ImportError: If httpx is not installed
        """
        if httpx is None:
            raise ImportError(
                "httpx is required for HTTP transport. "
                "Install it with: pip install xsp-lib[http]"
            )

        if client is None:
            limits = httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
                keepalive_expiry=keepalive_expiry,
            )
            self.client = httpx.AsyncClient(
                limits=limits,
                timeout=httpx.Timeout(timeout),
                follow_redirects=follow_redirects,
                verify=verify_ssl,
            )
            self._owns_client = True
        else:
            self.client = client
            self._owns_client = False

        self.method = method.upper()
        self.default_timeout = timeout

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
        Send HTTP request with error handling.

        Args:
            endpoint: URL to request
            payload: Optional request body
            metadata: Headers and parameters (params in "_params" key)
            timeout: Request timeout (overrides default)

        Returns:
            Response body as bytes

        Raises:
            TransportTimeoutError: Request timed out
            TransportConnectionError: Connection failed
            TransportError: HTTP error or other transport issue
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
        elif self.default_timeout is not None:
            request_args["timeout"] = self.default_timeout

        # Send request with error handling
        try:
            response = await self.client.request(**request_args)
            response.raise_for_status()
            return response.content

        except httpx.TimeoutException as e:
            raise TransportTimeoutError(
                f"Request timeout after {timeout or self.default_timeout}s: {endpoint}"
            ) from e

        except (httpx.ConnectError, httpx.NetworkError) as e:
            raise TransportConnectionError(
                f"Connection failed: {endpoint}"
            ) from e

        except httpx.HTTPStatusError as e:
            raise TransportError(
                f"HTTP {e.response.status_code} error: {endpoint}",
                status_code=e.response.status_code,
            ) from e

        except Exception as e:
            raise TransportError(f"Transport error: {endpoint}") from e

    async def close(self) -> None:
        """Close HTTP client if owned."""
        if self._owns_client:
            await self.client.aclose()
