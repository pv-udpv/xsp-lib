"""HTTP/HTTPS transport implementation."""

from typing import Any

from xsp.core.transport import TransportType

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore


class HttpTransport:
    """HTTP/HTTPS transport for REST APIs."""

    def __init__(
        self,
        client: Any | None = None,
        method: str = "GET",
    ):
        """
        Initialize HTTP transport.

        Args:
            client: Optional httpx.AsyncClient instance
            method: HTTP method (GET, POST, etc.)

        Raises:
            ImportError: If httpx is not installed
        """
        if httpx is None:
            raise ImportError(
                "httpx is required for HTTP transport. "
                "Install it with: pip install xsp-lib[http]"
            )

        self.client = client or httpx.AsyncClient()
        self.method = method.upper()
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

        # Send request
        response = await self.client.request(**request_args)
        response.raise_for_status()

        return response.content

    async def close(self) -> None:
        """Close HTTP client if owned."""
        if self._owns_client:
            await self.client.aclose()
