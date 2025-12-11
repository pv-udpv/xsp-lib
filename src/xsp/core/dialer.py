"""Dialer abstraction for managing connections to upstream services.

This module provides a Protocol-based abstraction for connection management,
enabling connection pooling, resource lifecycle management, and support for
multiple transport protocols (HTTP, gRPC).

The Dialer pattern separates connection establishment from request execution,
allowing for better resource management and testing in AdTech service integrations.

Example:
    >>> from xsp.core.dialer import HttpDialer
    >>>
    >>> # Create a dialer with connection pooling
    >>> dialer = HttpDialer(
    ...     pool_limits={"max_connections": 100, "max_keepalive_connections": 20},
    ...     timeout=30.0
    ... )
    >>>
    >>> # Use the dialer's client for requests
    >>> async with dialer:
    ...     response = await dialer.client.get("https://api.example.com/vast")
    >>>
    >>> # Or manage lifecycle manually
    >>> await dialer.close()
"""

from typing import Any, Protocol


class Dialer(Protocol):
    """Protocol for connection dialers to upstream services.

    Dialers manage the lifecycle of connections to remote services,
    providing connection pooling, timeout management, and resource cleanup.
    This abstraction enables testing with mock dialers and supports multiple
    transport protocols (HTTP, gRPC, WebSocket).

    Implementations should:
    - Manage connection pools efficiently
    - Support async context manager protocol
    - Provide configurable timeouts
    - Clean up resources on close

    Example:
        >>> class CustomDialer:
        ...     async def dial(self, endpoint: str) -> Connection:
        ...         # Establish connection with pooling
        ...         return await self._pool.get_connection(endpoint)
        ...
        ...     async def close(self) -> None:
        ...         await self._pool.close_all()
    """

    async def close(self) -> None:
        """Close all connections and release resources.

        This method should:
        - Close all active connections in the pool
        - Release any held resources (file handles, sockets)
        - Cancel any pending connection attempts
        - Be idempotent (safe to call multiple times)

        Raises:
            Exception: Implementation-specific cleanup errors
        """
        ...

    async def __aenter__(self) -> "Dialer":
        """Enter async context manager.

        Returns:
            The dialer instance for use in async with blocks
        """
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager and cleanup resources.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        ...


class HttpDialer:
    """HTTP/HTTPS dialer with connection pooling.

    Provides managed HTTP client connections with configurable pooling,
    timeouts, and resource lifecycle. Built on httpx.AsyncClient for
    high-performance async HTTP operations.

    This dialer is suitable for:
    - VAST/VPAID video ad serving (IAB VAST 3.0-4.2)
    - OpenRTB bid request/response (IAB OpenRTB 2.6, 3.0)
    - DAAST audio ad serving (deprecated, use VAST with adType="audio")
    - Any HTTP-based AdTech protocol integration

    Connection pooling helps manage resources when making frequent requests
    to upstream ad servers, DSPs, SSPs, and verification services.

    Args:
        pool_limits: Connection pool configuration with keys:
            - max_connections: Maximum total connections (default: 100)
            - max_keepalive_connections: Maximum idle keepalive connections (default: 20)
        timeout: Default timeout for all requests in seconds (default: 30.0)
        client: Optional pre-configured httpx.AsyncClient instance.
            If provided, pool_limits and timeout are ignored.

    Raises:
        ImportError: If httpx is not installed

    Example:
        >>> # Basic usage with defaults
        >>> dialer = HttpDialer()
        >>> async with dialer:
        ...     response = await dialer.client.get("https://example.com/vast")

        >>> # Custom pool configuration for high-traffic scenarios
        >>> dialer = HttpDialer(
        ...     pool_limits={
        ...         "max_connections": 200,
        ...         "max_keepalive_connections": 50
        ...     },
        ...     timeout=15.0
        ... )

        >>> # Use in VAST upstream
        >>> class VastUpstream:
        ...     def __init__(self, dialer: HttpDialer):
        ...         self.client = dialer.client
        ...
        ...     async def fetch(self, url: str) -> bytes:
        ...         response = await self.client.get(url)
        ...         return response.content

    References:
        - HTTPX Documentation: https://www.python-httpx.org/
        - IAB VAST 4.2: https://iabtechlab.com/vast (video ad serving)
        - IAB OpenRTB 2.6: https://iabtechlab.com/openrtb (real-time bidding)
    """

    def __init__(
        self,
        pool_limits: dict[str, int] | None = None,
        timeout: float = 30.0,
        client: Any | None = None,
    ):
        """Initialize HTTP dialer with connection pooling.

        Args:
            pool_limits: Connection pool configuration. Defaults to:
                {"max_connections": 100, "max_keepalive_connections": 20}
            timeout: Request timeout in seconds. Default: 30.0
            client: Optional pre-configured httpx.AsyncClient. If provided,
                pool_limits and timeout parameters are ignored.

        Raises:
            ImportError: If httpx is not installed
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for HttpDialer. " "Install it with: pip install xsp-lib[http]"
            )

        if client is not None:
            # Use provided client, ignore pool_limits and timeout
            self.client = client
            self._owns_client = False
        else:
            # Create client with pool configuration
            default_limits = {
                "max_connections": 100,
                "max_keepalive_connections": 20,
            }
            limits = {**default_limits, **(pool_limits or {})}

            # Create httpx.Limits object
            limits_obj = httpx.Limits(
                max_connections=limits["max_connections"],
                max_keepalive_connections=limits["max_keepalive_connections"],
            )

            self.client = httpx.AsyncClient(
                limits=limits_obj,
                timeout=timeout,
            )
            self._owns_client = True

    async def close(self) -> None:
        """Close HTTP client and release all connections.

        Closes all active and idle connections in the pool. Safe to call
        multiple times (idempotent). Only closes the client if this dialer
        created it (not if a client was provided to __init__).

        This should be called when:
        - Application shutdown
        - Service reconfiguration
        - Connection pool needs to be reset
        - Exiting async context manager

        Example:
            >>> dialer = HttpDialer()
            >>> # ... use dialer ...
            >>> await dialer.close()  # Clean shutdown
        """
        if self._owns_client:
            await self.client.aclose()

    async def __aenter__(self) -> "HttpDialer":
        """Enter async context manager.

        Returns:
            The HttpDialer instance for use in async with blocks

        Example:
            >>> async with HttpDialer() as dialer:
            ...     response = await dialer.client.get("https://api.example.com")
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager and close connections.

        Automatically closes the HTTP client when exiting the context,
        ensuring proper resource cleanup even if an exception occurred.

        Args:
            exc_type: Exception type if an error occurred in the context
            exc_val: Exception value if an error occurred in the context
            exc_tb: Exception traceback if an error occurred in the context
        """
        await self.close()
