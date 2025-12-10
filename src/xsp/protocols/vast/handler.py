<<<<<<< HEAD
"""VAST protocol handler implementation."""

from typing import Any

from xsp.core.protocol import AdRequest, AdResponse
from xsp.protocols.vast.chain_resolver import ChainResolver


class VastProtocolHandler:
    """
    VAST protocol handler.

    Maps generic AdRequest to VAST-specific parameters and delegates
    to ChainResolver for wrapper chain resolution.

    Implements ProtocolHandler protocol for use with Orchestrator.
    """

    def __init__(self, chain_resolver: ChainResolver) -> None:
=======
"""VAST protocol handler for orchestrator."""

from typing import Any

from xsp.orchestrator.protocol import ProtocolHandler
from xsp.orchestrator.schemas import AdRequest, AdResponse


class VastProtocolHandler(ProtocolHandler):
    """
    VAST protocol handler.

    Maps protocol-agnostic AdRequest/AdResponse to VAST-specific
    operations using VastUpstream.

    Example:
        # Create handler with VAST upstream
        from xsp.protocols.vast import VastUpstream
        from xsp.transports.http import HttpTransport

        transport = HttpTransport()
        vast_upstream = VastUpstream(
            transport=transport,
            endpoint="https://ads.example.com/vast",
        )

        handler = VastProtocolHandler(upstream=vast_upstream)

        # Use with orchestrator
        from xsp.orchestrator import Orchestrator

        orchestrator = Orchestrator(protocol_handler=handler)
        response = await orchestrator.fetch_ad(
            AdRequest(slot_id="pre-roll", user_id="user123")
        )
    """

    def __init__(self, upstream: Any):
>>>>>>> origin/main
        """
        Initialize VAST protocol handler.

        Args:
<<<<<<< HEAD
            chain_resolver: VAST chain resolver instance
        """
        self.chain_resolver = chain_resolver

    @property
    def protocol_name(self) -> str:
        """Return protocol name."""
        return "vast"

    async def handle(self, request: AdRequest) -> AdResponse:
        """
        Handle VAST ad request.

        Maps AdRequest fields to VAST query parameters:
        - user_id → uid parameter
        - ip_address → ip parameter
        - url → url parameter (content URL)
        - placement_id → placement_id parameter
        - Additional params from request.params

        Args:
            request: Universal ad request

        Returns:
            Ad response with VAST XML data
        """
        # Build VAST-specific parameters
        vast_params: dict[str, Any] = {}

        if request.user_id:
            vast_params["uid"] = request.user_id
        if request.ip_address:
            vast_params["ip"] = request.ip_address
        if request.url:
            vast_params["url"] = request.url
        if request.placement_id:
            vast_params["placement_id"] = request.placement_id

        # Merge with additional params from request
        vast_params.update(request.params)

        # Resolve VAST chain
        try:
            vast_xml = await self.chain_resolver.resolve(
                params=vast_params,
                headers=request.headers,
                context=request.context,
            )

            return AdResponse(
                protocol="vast",
                data=vast_xml,
                status="success",
                metadata={
                    "params": vast_params,
                    "user_id": request.user_id,
                    "ip_address": request.ip_address,
                },
            )
        except Exception as e:
            return AdResponse(
                protocol="vast",
                data="",
                status="error",
                error=str(e),
                metadata={
                    "params": vast_params,
                    "error_type": type(e).__name__,
                },
            )

    async def close(self) -> None:
        """Close chain resolver and release resources."""
        await self.chain_resolver.close()
=======
            upstream: VastUpstream instance for VAST operations

        Note:
            We use Any for upstream type to avoid circular import.
            In practice, this should be xsp.protocols.vast.VastUpstream.
        """
        self.upstream = upstream

    async def fetch(
        self,
        request: AdRequest,
        **context: object,
    ) -> AdResponse:
        """
        Fetch VAST ad and map to AdResponse.

        Maps AdRequest → VAST params → VAST XML → AdResponse

        Args:
            request: Protocol-agnostic ad request
            **context: Additional context

        Returns:
            Protocol-agnostic ad response

        Flow:
            1. Extract VAST-specific params from AdRequest
            2. Build VAST context for macros
            3. Fetch VAST XML via VastUpstream
            4. Parse VAST response (simplified - just returns XML)
            5. Map to AdResponse

        Note:
            This is a simplified implementation. A full implementation
            would parse VAST XML and extract creative details.
        """
        # Build VAST-specific params from generic request
        params: dict[str, Any] = {
            "uid": request["user_id"],
        }

        # Add optional VAST params
        if "ip_address" in request:
            params["ip"] = request["ip_address"]

        if "device_type" in request:
            params["device"] = request["device_type"]

        if "content_url" in request:
            params["url"] = request["content_url"]

        # Build VAST context for macro substitution
        vast_context: dict[str, Any] = {}
        if "playhead_position" in request:
            vast_context["contentplayhead"] = str(request["playhead_position"])

        # Fetch VAST XML
        try:
            xml = await self.upstream.fetch(
                params=params,
                context=vast_context,
            )

            # In a full implementation, parse XML to extract:
            # - creative_url, duration, bitrate
            # - tracking_urls
            # - ad_system, advertiser, etc.
            #
            # For now, return simplified response with raw XML
            return AdResponse(
                success=True,
                slot_id=request["slot_id"],
                ad_id="vast-ad",  # Would extract from XML
                creative_type="video/linear",
                raw_response=xml,
                extensions={
                    "vast_xml": xml,
                    "params": params,
                },
            )

        except Exception as e:
            return AdResponse(
                success=False,
                slot_id=request["slot_id"],
                error=str(e),
                error_code="VAST_FETCH_ERROR",
            )

    async def track(
        self,
        event: str,
        response: AdResponse,
        **context: object,
    ) -> None:
        """
        Track VAST event.

        Fires tracking URLs for the specified event.

        Args:
            event: Event type ('impression', 'click', 'complete', etc.)
            response: Ad response containing tracking URLs
            **context: Additional context

        Note:
            Full implementation would extract tracking URLs from
            VAST XML and fire them via HTTP transport.
        """
        # In full implementation:
        # 1. Extract tracking URLs from response
        # 2. Fire URLs for the event type
        tracking_urls = response.get("tracking_urls", {})
        urls = tracking_urls.get(event, [])

        # Fire tracking URLs (simplified - just log for now)
        for url in urls:
            # await self._fire_tracking_url(url)
            pass

    def validate_request(self, request: AdRequest) -> bool:
        """
        Validate VAST request has required fields.

        VAST requires:
        - slot_id: Slot identifier
        - user_id: User identifier

        Args:
            request: Ad request to validate

        Returns:
            True if request is valid for VAST protocol
        """
        return "slot_id" in request and "user_id" in request
>>>>>>> origin/main
