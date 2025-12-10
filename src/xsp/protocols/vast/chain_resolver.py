"""VAST wrapper chain resolver implementation.

Resolves VAST wrapper chains by recursively following VASTAdTagURI
elements until an InLine response is found or depth limit is reached.

References:
    - VAST 4.2 §2.4.3.4: Wrapper element and chain resolution
    - VAST 4.2 §2.4.1.2: maxwrapperdepth attribute
    - VAST 4.2 §2.4.4.1: MediaFile selection criteria
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any
from xml.etree import ElementTree as ET

from xsp.core.exceptions import UpstreamError, UpstreamTimeout

from .chain import VastChainConfig
from .types import VastResolutionResult

if TYPE_CHECKING:
    from .upstream import VastUpstream


class VastChainResolver:
    """VAST wrapper chain resolver.

    Resolves VAST wrapper chains by recursively following VASTAdTagURI
    elements from Wrapper responses until an InLine response is found.

    Supports:
    - Multiple upstream fallbacks
    - Configurable depth limits
    - Timeout protection
    - Error tracking and recovery

    Per VAST 4.2 §2.4.3.4 - Wrapper elements contain VASTAdTagURI that
    must be resolved to obtain the final InLine ad response.

    Example:
        >>> config = VastChainConfig(max_depth=5)
        >>> upstreams = {"primary": vast_upstream}
        >>> resolver = VastChainResolver(config, upstreams)
        >>> result = await resolver.resolve(params={"user": "123"})
    """

    def __init__(
        self,
        config: VastChainConfig,
        upstreams: dict[str, "VastUpstream"],
    ) -> None:
        """Initialize VAST chain resolver.

        Args:
            config: Resolution configuration
            upstreams: Dictionary of VastUpstream instances keyed by name.
                      First key is primary, remaining are fallbacks.

        Raises:
            ValueError: If upstreams dict is empty
        """
        if not upstreams:
            raise ValueError("At least one upstream must be provided")

        self.config = config
        self.upstreams = upstreams
        self._primary_key = next(iter(upstreams.keys()))
        self._fallback_keys = list(upstreams.keys())[1:]

    async def resolve(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> VastResolutionResult:
        """Resolve VAST wrapper chain to final InLine response.

        Attempts to resolve using primary upstream first, then falls back
        to secondary upstreams if enabled and primary fails.

        Args:
            params: Query parameters for upstream requests
            headers: HTTP headers for upstream requests
            context: Additional context for macro substitution
            **kwargs: Additional arguments passed to upstream

        Returns:
            VastResolutionResult containing resolved VAST and metadata

        Example:
            >>> result = await resolver.resolve(params={"w": "640", "h": "480"})
            >>> if result.success:
            ...     print(f"Resolved chain: {result.chain}")
        """
        start_time = time.perf_counter()

        # Merge additional params from config
        merged_params = {**(self.config.additional_params), **(params or {})}

        # Try primary upstream
        try:
            result = await self._resolve_upstream(
                upstream_key=self._primary_key,
                params=merged_params,
                headers=headers,
                context=context,
                **kwargs,
            )
            result.used_fallback = False
            result.resolution_time_ms = (time.perf_counter() - start_time) * 1000
            return result
        except Exception as primary_error:
            # Try fallbacks if enabled
            if self.config.enable_fallbacks and self._fallback_keys:
                for fallback_key in self._fallback_keys:
                    try:
                        result = await self._resolve_upstream(
                            upstream_key=fallback_key,
                            params=merged_params,
                            headers=headers,
                            context=context,
                            **kwargs,
                        )
                        result.used_fallback = True
                        result.resolution_time_ms = (time.perf_counter() - start_time) * 1000
                        return result
                    except Exception:
                        # Continue to next fallback
                        continue

            # All upstreams failed
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return VastResolutionResult(
                success=False,
                error=primary_error,
                used_fallback=False,
                resolution_time_ms=elapsed_ms,
            )

    async def _resolve_upstream(
        self,
        upstream_key: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> VastResolutionResult:
        """Resolve wrapper chain using specific upstream.

        Recursively follows wrapper chain until InLine is found or
        depth limit is reached.

        Args:
            upstream_key: Key of upstream to use
            params: Query parameters
            headers: HTTP headers
            context: Additional context
            **kwargs: Additional arguments

        Returns:
            VastResolutionResult with resolved data

        Raises:
            UpstreamError: If resolution fails
            UpstreamTimeout: If total timeout is exceeded
        """
        upstream = self.upstreams[upstream_key]
        chain: list[str] = []
        current_depth = 0

        # Initial fetch from upstream
        try:
            xml = await asyncio.wait_for(
                upstream.fetch(
                    params=params,
                    headers=headers,
                    context=context,
                    timeout=self.config.per_request_timeout,
                    **kwargs,
                ),
                timeout=self.config.timeout,
            )
        except TimeoutError as e:
            raise UpstreamTimeout(f"Initial fetch timed out after {self.config.timeout}s") from e

        # Track the endpoint URL (reconstruct from upstream)
        # For Phase 1, we'll use a placeholder
        initial_url = getattr(upstream, "endpoint", "unknown")
        chain.append(initial_url)

        # Parse initial response
        vast_data = self._parse_vast_xml(xml)

        # Follow wrapper chain
        while self._is_wrapper(xml) and current_depth < self.config.max_depth:
            current_depth += 1

            # Extract next URL from wrapper
            wrapper_url = self._extract_wrapper_url(xml)
            if not wrapper_url:
                raise UpstreamError("Wrapper missing VASTAdTagURI")

            chain.append(wrapper_url)

            # Fetch next in chain
            # For Phase 1, create a temporary upstream with the wrapper URL
            # In Phase 2, we'll add more sophisticated URL handling
            from .types import VastVersion
            from .upstream import VastUpstream

            # Get version from upstream if it's a VastUpstream
            version = getattr(upstream, "version", VastVersion.V4_2)
            if not isinstance(version, VastVersion):
                version = VastVersion.V4_2

            temp_upstream = VastUpstream(
                transport=upstream.transport,
                endpoint=wrapper_url,
                version=version,
                enable_macros=getattr(upstream, "macro_substitutor", None) is not None,
                validate_xml=getattr(upstream, "validate_xml", False),
            )

            try:
                xml = await asyncio.wait_for(
                    temp_upstream.fetch(
                        params=None,  # URL is complete
                        headers=headers,
                        context=context,
                        **kwargs,
                    ),
                    timeout=self.config.timeout,
                )
            except TimeoutError as e:
                raise UpstreamTimeout(f"Wrapper fetch timed out at depth {current_depth}") from e

            # Update vast_data with new response
            vast_data = self._parse_vast_xml(xml)

        # Check if we found InLine or hit depth limit
        if self._is_inline(xml):
            # Success - we have final InLine response
            # For Phase 1, creative selection is a stub
            selected_creative = self._select_creative(vast_data)

            return VastResolutionResult(
                success=True,
                vast_data=vast_data,
                selected_creative=selected_creative,
                chain=chain,
                xml=xml,
            )
        else:
            # Hit depth limit without finding InLine
            raise UpstreamError(f"Max wrapper depth ({self.config.max_depth}) exceeded")

    def _is_wrapper(self, xml: str) -> bool:
        """Check if VAST response is a Wrapper.

        Per VAST 4.2 §2.4.3.4 - Wrapper elements contain VASTAdTagURI
        that must be resolved to get the final InLine response.

        Args:
            xml: VAST XML string

        Returns:
            True if response contains Wrapper element
        """
        try:
            root = ET.fromstring(xml)
            # Check for Wrapper element
            # VAST structure: <VAST><Ad><Wrapper>
            wrapper = root.find(".//Wrapper")
            return wrapper is not None
        except ET.ParseError:
            return False

    def _is_inline(self, xml: str) -> bool:
        """Check if VAST response is InLine.

        Per VAST 4.2 §2.4.3.2 - InLine elements contain complete
        creative assets and are the terminal nodes in wrapper chains.

        Args:
            xml: VAST XML string

        Returns:
            True if response contains InLine element
        """
        try:
            root = ET.fromstring(xml)
            # Check for InLine element
            # VAST structure: <VAST><Ad><InLine>
            inline = root.find(".//InLine")
            return inline is not None
        except ET.ParseError:
            return False

    def _extract_wrapper_url(self, xml: str) -> str | None:
        """Extract VASTAdTagURI from Wrapper element.

        Per VAST 4.2 §2.4.3.4 - VASTAdTagURI contains the URL to the
        next VAST response in the wrapper chain.

        Args:
            xml: VAST XML string containing Wrapper

        Returns:
            URL string or None if not found
        """
        try:
            root = ET.fromstring(xml)
            # Find VASTAdTagURI in Wrapper
            # VAST structure: <VAST><Ad><Wrapper><VASTAdTagURI>
            vast_ad_tag_uri = root.find(".//Wrapper/VASTAdTagURI")
            if vast_ad_tag_uri is not None and vast_ad_tag_uri.text:
                # Strip whitespace and CDATA
                return vast_ad_tag_uri.text.strip()
            return None
        except ET.ParseError:
            return None

    def _parse_vast_xml(self, xml: str) -> dict[str, Any]:
        """Parse VAST XML into dictionary structure.

        Basic parser for Phase 1. Will be enhanced in Phase 2 with
        full VAST structure parsing.

        Args:
            xml: VAST XML string

        Returns:
            Dictionary with parsed VAST data
        """
        try:
            root = ET.fromstring(xml)
            vast_data: dict[str, Any] = {
                "version": root.get("version", "unknown"),
                "ads": [],
            }

            # Parse basic Ad structure
            for ad in root.findall(".//Ad"):
                ad_data = {
                    "id": ad.get("id"),
                    "type": None,
                }

                # Check if InLine or Wrapper
                if ad.find("InLine") is not None:
                    ad_data["type"] = "InLine"
                    inline = ad.find("InLine")
                    if inline is not None:
                        ad_data["ad_system"] = self._get_text(inline, "AdSystem")
                        ad_data["ad_title"] = self._get_text(inline, "AdTitle")
                elif ad.find("Wrapper") is not None:
                    ad_data["type"] = "Wrapper"

                vast_data["ads"].append(ad_data)

            return vast_data
        except ET.ParseError:
            return {"version": "unknown", "ads": []}

    def _get_text(self, element: ET.Element, tag: str) -> str | None:
        """Get text content from XML element.

        Args:
            element: Parent element
            tag: Tag name to find

        Returns:
            Text content or None
        """
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None

    def _select_creative(self, vast_data: dict[str, Any]) -> dict[str, Any] | None:
        """Select creative from resolved VAST response.

        Stub implementation for Phase 1. Will be fully implemented in Phase 2
        with proper media file selection based on bitrate, resolution, etc.

        Per VAST 4.2 §2.4.4.1 - MediaFile selection based on delivery method,
        dimensions, bitrate, codec, and scalability.

        Args:
            vast_data: Parsed VAST data dictionary

        Returns:
            Selected creative dict or None
        """
        # Phase 1 stub: Return first ad if available
        ads = vast_data.get("ads")
        if ads and isinstance(ads, list) and len(ads) > 0:
            first_ad: dict[str, Any] = ads[0]
            return first_ad
        return None
