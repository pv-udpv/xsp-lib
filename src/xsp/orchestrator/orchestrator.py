"""Protocol-agnostic ad orchestrator implementation."""

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any

from xsp.orchestrator.protocol import ProtocolHandler
from xsp.orchestrator.schemas import AdRequest, AdResponse


class CacheBackend(ABC):
    """
    Abstract cache backend interface.

    Concrete implementations should provide actual caching
    (Redis, Memory, etc.).
    """

    @abstractmethod
    async def get(self, key: str) -> AdResponse | None:
        """Get cached response by key."""
        ...

    @abstractmethod
    async def set(self, key: str, value: AdResponse, ttl: int) -> None:
        """Set cached response with TTL in seconds."""
        ...


class Orchestrator:
    """
    Protocol-agnostic ad orchestrator.

    Provides unified interface for ad serving across multiple protocols
    (VAST, VMAP, OpenRTB, custom) with common cross-cutting concerns:
    - Request validation
    - Response caching (protocol-agnostic)
    - Event tracking
    - Error handling

    The orchestrator delegates protocol-specific operations to
    ProtocolHandler implementations while managing caching and
    coordination.

    Usage:
        # Create with protocol handler
        orchestrator = Orchestrator(
            protocol_handler=VastProtocolHandler(...),
            cache=MemoryCache(),
            enable_caching=True,
            cache_ttl=3600,
        )

        # Fetch ad
        response = await orchestrator.fetch_ad(
            AdRequest(
                slot_id="pre-roll",
                user_id="user123",
                device_type="mobile",
            )
        )

        # Track event
        if response["success"]:
            await orchestrator.track_event("impression", response)

    Configuration from file:
        orchestrator = Orchestrator.from_config("config/vast.yaml")
        response = await orchestrator.fetch_ad(request)
    """

    def __init__(
        self,
        protocol_handler: ProtocolHandler,
        cache: CacheBackend | None = None,
        enable_caching: bool = True,
        cache_ttl: int = 3600,
    ):
        """
        Initialize orchestrator.

        Args:
            protocol_handler: Protocol-specific handler implementation
            cache: Optional cache backend (None = no caching)
            enable_caching: Enable/disable caching
            cache_ttl: Cache TTL in seconds (default: 1 hour)
        """
        self.handler = protocol_handler
        self.cache = cache
        self.enable_caching = enable_caching and cache is not None
        self.cache_ttl = cache_ttl

    @classmethod
    def from_config(cls, config_path: str) -> "Orchestrator":
        """
        Create orchestrator from YAML configuration file.

        Configuration determines which protocol handler to use and
        how to configure it:
        - vast.yaml → VastProtocolHandler
        - vmap.yaml → VmapProtocolHandler
        - openrtb.yaml → OpenRTBProtocolHandler

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Configured Orchestrator instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid

        Note:
            This method will be implemented once config_loader module
            is added (Phase 4).
        """
        raise NotImplementedError(
            "Configuration loading will be implemented in Phase 4. "
            "Use Orchestrator(...) constructor directly for now."
        )

    async def fetch_ad(
        self,
        request: AdRequest,
    ) -> AdResponse:
        """
        Fetch ad using protocol-agnostic interface.

        Flow:
        1. Validate request has required fields
        2. Check cache for existing response
        3. If cache miss, fetch via protocol handler
        4. Cache successful responses
        5. Return normalized response

        Args:
            request: Protocol-agnostic ad request

        Returns:
            Protocol-agnostic ad response

        Examples:
            VAST request:
                response = await orchestrator.fetch_ad(
                    AdRequest(
                        slot_id="pre-roll",
                        user_id="user123",
                        device_type="mobile",
                        playhead_position=0.0,
                    )
                )

            OpenRTB request:
                response = await orchestrator.fetch_ad(
                    AdRequest(
                        slot_id="banner-top",
                        user_id="user123",
                        player_size=(728, 90),
                        geo={"country": "US"},
                    )
                )
        """
        # Validate request
        if not self.handler.validate_request(request):
            return AdResponse(
                success=False,
                slot_id=request.get("slot_id", "unknown"),
                error="Invalid request: missing required fields for protocol",
            )

        # Check cache
        if self.enable_caching:
            cached = await self._get_from_cache(request)
            if cached is not None:
                # Mark as cached
                cached_copy: AdResponse = dict(cached)  # type: ignore
                cached_copy["cached"] = True
                return cached_copy

        # Fetch via protocol handler
        response = await self.handler.fetch(request)

        # Cache successful responses
        if self.enable_caching and response["success"]:
            await self._save_to_cache(request, response)

        return response

    async def track_event(
        self,
        event: str,
        response: AdResponse,
    ) -> None:
        """
        Track ad event (protocol-agnostic).

        Delegates to protocol handler for protocol-specific tracking
        implementation (firing tracking URLs, etc.).

        Args:
            event: Event type ('impression', 'click', 'complete', 'error', etc.)
            response: Ad response from fetch_ad() containing tracking info

        Examples:
            # Track impression
            await orchestrator.track_event("impression", response)

            # Track click
            await orchestrator.track_event("click", response)

            # Track video complete
            await orchestrator.track_event("complete", response)
        """
        await self.handler.track(event, response)

    async def _get_from_cache(self, request: AdRequest) -> AdResponse | None:
        """
        Get cached response for request.

        Args:
            request: Ad request to look up

        Returns:
            Cached response or None if not found
        """
        if not self.cache:
            return None

        cache_key = self._make_cache_key(request)
        return await self.cache.get(cache_key)

    async def _save_to_cache(
        self, request: AdRequest, response: AdResponse
    ) -> None:
        """
        Save response to cache.

        Args:
            request: Ad request (for cache key)
            response: Ad response to cache
        """
        if not self.cache:
            return

        cache_key = self._make_cache_key(request)
        await self.cache.set(cache_key, response, ttl=self.cache_ttl)

    def _make_cache_key(self, request: AdRequest) -> str:
        """
        Generate cache key from request.

        Creates deterministic cache key from request fields,
        excluding extensions to ensure consistent caching.

        Uses SHA-256 for cryptographic security.

        Args:
            request: Ad request

        Returns:
            Cache key string (e.g., "ad:abc123...")
        """
        # Create key from request, excluding extensions
        key_data: dict[str, Any] = {
            k: v for k, v in request.items() if k not in ["extensions"]
        }

        # Sort keys for deterministic output
        key_json = json.dumps(key_data, sort_keys=True)

        # Hash to fixed-length key using SHA-256
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()

        return f"ad:{key_hash}"
