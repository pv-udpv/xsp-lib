"""Protocol-agnostic orchestrator for ad serving.

Provides high-level API for serving ads across multiple protocols
with caching, error handling, and protocol routing.
"""

from typing import cast

from xsp.core.protocol import AdRequest, AdResponse, ProtocolHandler
from xsp.core.state import StateBackend


class ProtocolNotSupportedError(Exception):
    """Requested protocol is not supported."""


class Orchestrator:
    """
    Protocol-agnostic orchestrator.

    Routes ad requests to appropriate protocol handlers (VAST, OpenRTB, DAAST)
    with optional caching and unified error handling.

    Provides high-level serve() API for ad serving.
    """

    def __init__(
        self,
        *,
        handlers: dict[str, ProtocolHandler] | None = None,
        cache_backend: StateBackend | None = None,
        enable_caching: bool = False,
        cache_ttl: float = 300.0,
    ) -> None:
        """
        Initialize orchestrator.

        Args:
            handlers: Protocol handlers by name (vast, openrtb, daast, etc.)
            cache_backend: Optional state backend for caching
            enable_caching: Enable response caching
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)

        Example:
            ```python
            from xsp.orchestrator import Orchestrator
            from xsp.protocols.vast.handler import VastProtocolHandler

            orchestrator = Orchestrator(
                handlers={"vast": vast_handler},
                enable_caching=True,
            )

            response = await orchestrator.serve(request)
            ```
        """
        self.handlers = handlers or {}
        self.cache_backend = cache_backend
        self.enable_caching = enable_caching and cache_backend is not None
        self.cache_ttl = cache_ttl

    def register_handler(self, protocol: str, handler: ProtocolHandler) -> None:
        """
        Register a protocol handler.

        Args:
            protocol: Protocol name (vast, openrtb, daast, etc.)
            handler: Protocol handler implementation
        """
        self.handlers[protocol] = handler

    async def serve(self, request: AdRequest) -> AdResponse:
        """
        Serve an ad request.

        Routes request to appropriate protocol handler based on request.protocol.
        Optionally uses caching if enabled.

        Args:
            request: Universal ad request

        Returns:
            Universal ad response

        Raises:
            ProtocolNotSupportedError: If protocol is not registered
        """
        # Determine protocol
        protocol = request.protocol or self._detect_protocol(request)

        if protocol not in self.handlers:
            return AdResponse(
                protocol=protocol or "unknown",
                data="",
                status="error",
                error=f"Protocol '{protocol}' not supported",
                metadata={
                    "supported_protocols": list(self.handlers.keys()),
                },
            )

        # Check cache if enabled
        cache_key = None
        if self.enable_caching and self.cache_backend:
            cache_key = self._build_cache_key(request, protocol)
            cached_response = await self.cache_backend.get(cache_key)
            if cached_response is not None and isinstance(cached_response, AdResponse):
                # Type is checked by isinstance, safe to cast
                return cast(AdResponse, cached_response)

        # Get handler and process request
        handler = self.handlers[protocol]
        response = await handler.handle(request)

        # Cache successful responses
        if (
            self.enable_caching
            and self.cache_backend
            and cache_key
            and response.status == "success"
        ):
            await self.cache_backend.set(
                cache_key,
                response,
                ttl=self.cache_ttl,
            )

        return response

    def _detect_protocol(self, request: AdRequest) -> str:
        """
        Auto-detect protocol from request parameters.

        Simple heuristic based on available handlers and request params.
        Defaults to "vast" if only one handler registered.

        Args:
            request: Ad request

        Returns:
            Detected protocol name
        """
        # If only one handler, use it
        if len(self.handlers) == 1:
            return next(iter(self.handlers.keys()))

        # Otherwise default to vast
        return "vast"

    def _build_cache_key(self, request: AdRequest, protocol: str) -> str:
        """
        Build cache key from request.

        Args:
            request: Ad request
            protocol: Protocol name

        Returns:
            Cache key string
        """
        import hashlib
        import json

        # Build deterministic key from request attributes
        key_data = {
            "protocol": protocol,
            "user_id": request.user_id,
            "ip_address": request.ip_address,
            "url": request.url,
            "placement_id": request.placement_id,
            "params": sorted(request.params.items()) if request.params else [],
        }

        # Hash to create compact key
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()

        return f"ad:{protocol}:{key_hash}"

    async def close(self) -> None:
        """Close all handlers and cache backend."""
        # Close all handlers
        for handler in self.handlers.values():
            await handler.close()

        # Close cache backend
        if self.cache_backend:
            await self.cache_backend.close()
