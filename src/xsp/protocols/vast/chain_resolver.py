"""VAST wrapper chain resolution.

Resolves VAST wrapper chains following redirects until reaching an inline ad.
Implements max depth protection per VAST 4.2 §3.4.1 recommendations.
"""

import asyncio
from typing import Any
from xml.etree import ElementTree as ET

from xsp.core.exceptions import UpstreamError, ValidationError
from xsp.core.types import Context, Headers
from xsp.protocols.vast.upstream import VastUpstream


class ChainResolutionError(UpstreamError):
    """VAST wrapper chain resolution failed."""


class MaxDepthExceededError(ChainResolutionError):
    """Maximum wrapper depth exceeded."""


class ChainResolver:
    """
    VAST wrapper chain resolver.

    Resolves VAST wrapper chains by following redirects until an inline
    ad is reached. Implements session support for cookie/header propagation
    and max depth protection per VAST 4.2 recommendations.

    Per VAST 4.2 §3.4.1: "Players should support at least 5 wrapper redirects"
    Default max depth is 5 but can be configured.
    """

    def __init__(
        self,
        upstream: VastUpstream,
        *,
        max_depth: int = 5,
        propagate_headers: bool = True,
    ) -> None:
        """
        Initialize chain resolver.

        Args:
            upstream: VAST upstream for fetching VAST documents
            max_depth: Maximum wrapper chain depth (default 5 per VAST 4.2)
            propagate_headers: Propagate session headers across redirects
        """
        self.upstream = upstream
        self.max_depth = max_depth
        self.propagate_headers = propagate_headers

    async def resolve(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: Headers | None = None,
        context: Context | None = None,
    ) -> str:
        """
        Resolve VAST wrapper chain.

        Follows wrapper redirects until:
        1. An inline ad is found
        2. Max depth is reached (raises MaxDepthExceededError)
        3. An error occurs (raises ChainResolutionError)

        Args:
            params: Initial query parameters
            headers: Session headers (propagated if propagate_headers=True)
            context: Macro substitution context

        Returns:
            Final VAST XML (inline ad or last wrapper)

        Raises:
            MaxDepthExceededError: If max depth exceeded
            ChainResolutionError: If resolution fails
            ValidationError: If XML is malformed
        """
        current_params = params
        current_headers = headers
        depth = 0
        vast_chain: list[str] = []

        while depth < self.max_depth:
            # Fetch VAST document
            try:
                vast_xml = await self.upstream.fetch(
                    params=current_params,
                    headers=current_headers,
                    context=context,
                )
            except Exception as e:
                raise ChainResolutionError(
                    f"Failed to fetch VAST at depth {depth}: {e}"
                ) from e

            vast_chain.append(vast_xml)

            # Parse XML to check for wrapper
            try:
                root = ET.fromstring(vast_xml)
            except ET.ParseError as e:
                raise ValidationError(f"Invalid VAST XML at depth {depth}: {e}") from e

            # Check if this is a wrapper or inline
            ad = root.find(".//Ad")
            if ad is None:
                # Empty VAST or no ads
                return vast_xml

            wrapper = ad.find("Wrapper")
            if wrapper is None:
                # Found inline ad
                return vast_xml

            # Extract wrapper redirect URL
            vast_ad_tag_uri = wrapper.find("VASTAdTagURI")
            if vast_ad_tag_uri is None or not vast_ad_tag_uri.text:
                # Wrapper without redirect (malformed)
                raise ChainResolutionError(
                    f"Wrapper at depth {depth} missing VASTAdTagURI"
                )

            redirect_url = vast_ad_tag_uri.text.strip()

            # Update params for next fetch (redirect to new endpoint)
            # Clear previous params and use redirect URL as endpoint
            current_params = None
            if self.propagate_headers:
                # Keep headers for session continuity
                current_headers = headers
            else:
                current_headers = None

            # Update upstream endpoint for next iteration
            # Note: We'll need to create a new fetch with the redirect URL
            # For now, we update the upstream's endpoint
            self.upstream.endpoint = redirect_url

            depth += 1

        # Max depth reached
        raise MaxDepthExceededError(
            f"Maximum wrapper depth ({self.max_depth}) exceeded. "
            f"Chain: {depth} wrappers"
        )

    async def resolve_with_timeout(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: Headers | None = None,
        context: Context | None = None,
        timeout: float = 30.0,
    ) -> str:
        """
        Resolve VAST wrapper chain with timeout.

        Args:
            params: Initial query parameters
            headers: Session headers
            context: Macro substitution context
            timeout: Total timeout for entire resolution chain

        Returns:
            Final VAST XML

        Raises:
            asyncio.TimeoutError: If timeout exceeded
            MaxDepthExceededError: If max depth exceeded
            ChainResolutionError: If resolution fails
        """
        return await asyncio.wait_for(
            self.resolve(params=params, headers=headers, context=context),
            timeout=timeout,
        )

    async def close(self) -> None:
        """Close upstream and release resources."""
        await self.upstream.close()
