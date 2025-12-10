"""VAST protocol handler implementation."""

from typing import Any

from xsp.core.protocol import AdRequest, AdResponse, ProtocolHandler
from xsp.protocols.vast.chain_resolver import ChainResolver


class VastProtocolHandler:
    """
    VAST protocol handler.

    Maps generic AdRequest to VAST-specific parameters and delegates
    to ChainResolver for wrapper chain resolution.

    Implements ProtocolHandler protocol for use with Orchestrator.
    """

    def __init__(self, chain_resolver: ChainResolver) -> None:
        """
        Initialize VAST protocol handler.

        Args:
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
