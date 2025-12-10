"""VAST wrapper chain resolver implementation.

Resolves VAST wrapper chains by recursively following VASTAdTagURI
elements until an InLine response is found or depth limit is reached.

References:
    - VAST 4.2 §2.4.3.4: Wrapper element and chain resolution
    - VAST 4.2 §2.4.1.2: maxwrapperdepth attribute
    - VAST 4.2 §2.4.4.1: MediaFile selection criteria
"""

import asyncio
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from xml.etree import ElementTree as ET

from lxml import etree

from xsp.core.exceptions import UpstreamError, UpstreamTimeout

from .chain import SelectionStrategy, VastChainConfig
from .types import VastResolutionResult

if TYPE_CHECKING:
    from .upstream import VastUpstream

logger = logging.getLogger(__name__)


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
        self._custom_selector: Callable[[list[dict[str, Any]]], dict[str, Any] | None] | None = None

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
        depth limit is reached. Collects impression and error URLs
        from each wrapper in the chain.

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

        # Accumulate tracking data from chain
        all_impressions: list[str] = []
        all_error_urls: list[str] = []

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

        # Parse initial response and collect tracking data
        vast_data = self._parse_vast_xml(xml)
        if self.config.collect_tracking_urls:
            all_impressions.extend(self._collect_impressions(xml))
        if self.config.collect_error_urls:
            all_error_urls.extend(self._collect_error_urls(xml))

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

            # Update vast_data with new response and collect tracking data
            vast_data = self._parse_vast_xml(xml)
            if self.config.collect_tracking_urls:
                all_impressions.extend(self._collect_impressions(xml))
            if self.config.collect_error_urls:
                all_error_urls.extend(self._collect_error_urls(xml))

        # Check if we found InLine or hit depth limit
        if self._is_inline(xml):
            # Success - we have final InLine response
            # Add accumulated tracking data to vast_data
            vast_data["impressions"] = all_impressions
            vast_data["error_urls"] = all_error_urls

            # Select creative based on strategy
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

        Enhanced parser for Phase 2 with full VAST structure parsing
        including MediaFiles, tracking events, and creative data.

        Per VAST 4.2 §2.4.3.2 - InLine elements contain complete
        creative assets including MediaFiles.

        Args:
            xml: VAST XML string

        Returns:
            Dictionary with parsed VAST data
        """
        try:
            root = etree.fromstring(xml.encode("utf-8"))
            vast_data: dict[str, Any] = {
                "version": root.get("version", "unknown"),
                "ads": [],
                "ad_system": None,
                "ad_title": None,
                "media_files": [],
                "tracking_events": {},
            }

            # Parse Ad structure
            ad_elements = root.xpath("//Ad")
            if not isinstance(ad_elements, list):
                return vast_data

            for ad_elem in ad_elements:
                from lxml.etree import _Element

                if not isinstance(ad_elem, _Element):
                    continue

                ad_data: dict[str, Any] = {
                    "id": ad_elem.get("id"),
                    "type": None,
                }

                # Check if InLine or Wrapper
                inline = ad_elem.find("InLine")
                if inline is not None and isinstance(inline, _Element):
                    ad_data["type"] = "InLine"

                    # Extract Ad System
                    ad_system_elem = inline.find("AdSystem")
                    if ad_system_elem is not None and isinstance(ad_system_elem, _Element):
                        text = ad_system_elem.text
                        if text is not None:
                            ad_data["ad_system"] = text.strip()
                            vast_data["ad_system"] = text.strip()

                    # Extract Ad Title
                    ad_title_elem = inline.find("AdTitle")
                    if ad_title_elem is not None and isinstance(ad_title_elem, _Element):
                        text = ad_title_elem.text
                        if text is not None:
                            ad_data["ad_title"] = text.strip()
                            vast_data["ad_title"] = text.strip()

                    # Extract MediaFiles from Linear creatives
                    media_files = []
                    media_file_elements = inline.xpath(".//Creative/Linear/MediaFiles/MediaFile")
                    if isinstance(media_file_elements, list):
                        for mf_elem in media_file_elements:
                            if not isinstance(mf_elem, _Element):
                                continue

                            media_data: dict[str, Any] = {
                                "delivery": mf_elem.get("delivery"),
                                "type": mf_elem.get("type"),
                                "width": mf_elem.get("width"),
                                "height": mf_elem.get("height"),
                                "bitrate": mf_elem.get("bitrate"),
                                "uri": None,
                            }

                            text = mf_elem.text
                            if text is not None:
                                media_data["uri"] = text.strip()

                            if media_data["width"]:
                                media_data["width"] = int(media_data["width"])
                            if media_data["height"]:
                                media_data["height"] = int(media_data["height"])
                            if media_data["bitrate"]:
                                media_data["bitrate"] = int(media_data["bitrate"])

                            media_files.append(media_data)

                    ad_data["media_files"] = media_files
                    vast_data["media_files"] = media_files

                    # Extract tracking events
                    tracking_events: dict[str, list[str]] = {}
                    tracking_elements = inline.xpath(".//Creative/Linear/TrackingEvents/Tracking")
                    if isinstance(tracking_elements, list):
                        for track_elem in tracking_elements:
                            if not isinstance(track_elem, _Element):
                                continue

                            event_type = track_elem.get("event")
                            text = track_elem.text
                            if event_type and text:
                                url = text.strip()
                                if event_type not in tracking_events:
                                    tracking_events[event_type] = []
                                tracking_events[event_type].append(url)

                    ad_data["tracking_events"] = tracking_events
                    vast_data["tracking_events"] = tracking_events

                elif ad_elem.find("Wrapper") is not None:
                    ad_data["type"] = "Wrapper"

                vast_data["ads"].append(ad_data)

            return vast_data
        except etree.XMLSyntaxError:
            return {
                "version": "unknown",
                "ads": [],
                "ad_system": None,
                "ad_title": None,
                "media_files": [],
                "tracking_events": {},
            }

    def _collect_impressions(self, xml: str) -> list[str]:
        """Collect impression URLs from VAST XML.

        Args:
            xml: VAST XML string

        Returns:
            List of impression URL strings
        """
        try:
            root = etree.fromstring(xml.encode("utf-8"))
            impressions = []

            impression_elements = root.xpath("//Impression")
            if isinstance(impression_elements, list):
                from lxml.etree import _Element

                for elem in impression_elements:
                    if isinstance(elem, _Element):
                        text = elem.text
                        if text:
                            url = text.strip()
                            if url:
                                impressions.append(url)

            return impressions
        except etree.XMLSyntaxError:
            return []

    def _collect_error_urls(self, xml: str) -> list[str]:
        """Collect error tracking URLs from VAST XML.

        Args:
            xml: VAST XML string

        Returns:
            List of error tracking URL strings
        """
        try:
            root = etree.fromstring(xml.encode("utf-8"))
            error_urls = []

            error_elements = root.xpath("//Error")
            if isinstance(error_elements, list):
                from lxml.etree import _Element

                for elem in error_elements:
                    if isinstance(elem, _Element):
                        text = elem.text
                        if text:
                            url = text.strip()
                            if url:
                                error_urls.append(url)

            return error_urls
        except etree.XMLSyntaxError:
            return []

    def set_custom_selector(
        self, selector: Callable[[list[dict[str, Any]]], dict[str, Any] | None]
    ) -> None:
        """Set custom creative selection function.

        Args:
            selector: Function that takes list of media files and returns selected one
        """
        self._custom_selector = selector

    async def _track_fallback(self, result: VastResolutionResult) -> None:
        """Track when fallback upstream is used.

        Args:
            result: Resolution result containing fallback information
        """
        logger.info(
            "Fallback upstream used for VAST resolution. "
            f"Chain depth: {len(result.chain)}, "
            f"Resolution time: {result.resolution_time_ms:.2f}ms"
        )

    async def _track_error(self, error_urls: list[str], error_code: str = "900") -> None:
        """Send error tracking URLs.

        Args:
            error_urls: List of error tracking URLs to fire
            error_code: VAST error code (default: 900 = undefined error)
        """
        if not error_urls:
            return

        expanded_urls = [url.replace("[ERRORCODE]", error_code) for url in error_urls]

        for url in expanded_urls:
            asyncio.create_task(self._send_tracking_pixel(url, "error"))

    async def _track_impression(self, impression_urls: list[str]) -> None:
        """Send impression tracking pixels.

        Args:
            impression_urls: List of impression tracking URLs to fire
        """
        if not impression_urls:
            return

        for url in impression_urls:
            asyncio.create_task(self._send_tracking_pixel(url, "impression"))

    async def _send_tracking_pixel(self, url: str, pixel_type: str) -> None:
        """Send individual tracking pixel (fire-and-forget).

        Args:
            url: Tracking URL to fire
            pixel_type: Type of tracking (impression, error, etc.) for logging
        """
        try:
            primary_upstream = self.upstreams[self._primary_key]
            transport = primary_upstream.transport

            await asyncio.wait_for(
                transport.send(endpoint=url, payload=None, metadata=None, timeout=5.0),
                timeout=5.0,
            )

            logger.debug(f"Successfully sent {pixel_type} tracking pixel: {url}")

        except TimeoutError:
            logger.warning(f"Timeout sending {pixel_type} tracking pixel: {url}")
        except Exception as e:
            logger.warning(f"Error sending {pixel_type} tracking pixel {url}: {e}")

    def _select_creative(self, vast_data: dict[str, Any]) -> dict[str, Any] | None:
        """Select creative from resolved VAST response.

        Args:
            vast_data: Parsed VAST data dictionary

        Returns:
            Selected creative dict with selected_media_file or None

        Raises:
            UpstreamError: If CUSTOM strategy is used without custom selector
        """
        media_files = vast_data.get("media_files", [])
        if not media_files:
            return None

        strategy = self.config.selection_strategy
        selected_media: dict[str, Any] | None = None

        if strategy == SelectionStrategy.HIGHEST_BITRATE:
            files_with_bitrate = [f for f in media_files if f.get("bitrate") is not None]
            if files_with_bitrate:
                selected_media = max(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
            elif media_files:
                selected_media = media_files[0]

        elif strategy == SelectionStrategy.LOWEST_BITRATE:
            files_with_bitrate = [f for f in media_files if f.get("bitrate") is not None]
            if files_with_bitrate:
                selected_media = min(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
            elif media_files:
                selected_media = media_files[0]

        elif strategy == SelectionStrategy.BEST_QUALITY:
            files_with_bitrate = [f for f in media_files if f.get("bitrate") is not None]
            if files_with_bitrate:
                highest = max(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
                if highest.get("bitrate", 0) >= 1000:
                    selected_media = highest
                else:
                    selected_media = min(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
            elif media_files:
                selected_media = media_files[0]

        elif strategy == SelectionStrategy.CUSTOM:
            if self._custom_selector is None:
                raise UpstreamError(
                    "CUSTOM selection strategy requires custom selector function. "
                    "Call set_custom_selector() first."
                )
            selected_media = self._custom_selector(media_files)

        if selected_media:
            ads = vast_data.get("ads", [])
            first_ad = ads[0] if ads else {}

            return {
                "type": first_ad.get("type", "InLine"),
                "ad_id": first_ad.get("id"),
                "ad_system": vast_data.get("ad_system"),
                "ad_title": vast_data.get("ad_title"),
                "selected_media_file": selected_media,
                "all_media_files": media_files,
            }

        return None
