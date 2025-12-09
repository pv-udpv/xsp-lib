"""VAST and VMAP upstream implementations."""

from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from xsp.core.base import BaseUpstream
from xsp.core.transport import Transport

from .macros import MacroSubstitutor
from .types import VastVersion
from .validation import validate_vast_xml


class VastUpstream(BaseUpstream[str]):
    """
    VAST upstream for video ad serving.

    Supports:
    - VAST 2.0, 3.0, 4.0, 4.1, 4.2
    - VPAID (JavaScript/Flash creative)
    - IAB macro substitution ([TIMESTAMP], [CACHEBUSTING], etc.)
    - Flexible query parameter encoding (including Cyrillic)
    - VMAP support via VmapUpstream subclass
    """

    def __init__(
        self,
        transport: Transport,
        endpoint: str,
        *,
        version: VastVersion = VastVersion.V4_2,
        enable_macros: bool = True,
        validate_xml: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Initialize VAST upstream.

        Args:
            transport: Transport implementation
            endpoint: VAST ad server URL
            version: Expected VAST version
            enable_macros: Enable IAB macro substitution
            validate_xml: Validate XML structure after fetch
            **kwargs: Passed to BaseUpstream
        """
        super().__init__(
            transport=transport,
            decoder=lambda b: b.decode("utf-8"),
            endpoint=endpoint,
            **kwargs,
        )
        self.version = version
        self.validate_xml = validate_xml
        self.macro_substitutor = MacroSubstitutor() if enable_macros else None

    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Fetch VAST XML from upstream.

        Args:
            params: Query parameters for VAST request
            headers: HTTP headers
            context: Macro substitution context (playhead, error code, etc.)
            **kwargs: Additional arguments

        Returns:
            VAST XML string
        """
        # Build endpoint with params and apply macro substitution
        if params:
            endpoint = self._build_url_with_params(self.endpoint, params)
        else:
            endpoint = self.endpoint

        if self.macro_substitutor and context:
            endpoint = self.macro_substitutor.substitute(endpoint, context)

        # Fetch via parent
        xml = await super().fetch(
            endpoint=endpoint,
            params=None,  # Already in URL
            headers=headers,
            context=context,
            **kwargs,
        )

        # Validate if enabled
        if self.validate_xml:
            validate_vast_xml(xml)

        return xml

    def _build_url_with_params(self, base: str, params: dict[str, Any]) -> str:
        """
        Build URL with query parameters.

        Supports special encoding rules:
        - Pass `_encoding_config` dict to control per-param encoding
        - Example: {"url": False} to preserve Cyrillic in 'url' param

        Args:
            base: Base URL
            params: Query parameters

        Returns:
            URL with encoded parameters
        """
        # Extract encoding config
        encoding_config = params.pop("_encoding_config", {})

        # Parse existing query params from base
        parsed = urlparse(base)
        existing_params = parse_qs(parsed.query, keep_blank_values=True)

        # Flatten existing params (parse_qs returns lists)
        flat_existing = {k: v[0] if v else "" for k, v in existing_params.items()}

        # Merge with new params
        merged = {**flat_existing, **params}

        # Build query string with encoding control
        query_parts = []
        for key, value in merged.items():
            encoded_key = urlencode({key: ""})[:-1]  # Encode key

            # Check if we should skip encoding for this param
            if key in encoding_config and not encoding_config[key]:
                # Don't encode value (e.g., preserve Cyrillic)
                query_parts.append(f"{encoded_key}={value}")
            else:
                # Normal encoding
                query_parts.append(urlencode({key: value}))

        query = "&".join(query_parts)

        # Rebuild URL
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{query}"

    async def fetch_vast(
        self,
        *,
        user_id: str | None = None,
        ip_address: str | None = None,
        url: str | None = None,
        params: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Convenience method for VAST-specific parameters.

        Args:
            user_id: User identifier
            ip_address: Client IP address
            url: Content URL (may contain Cyrillic)
            params: Additional parameters
            context: Macro context
            **kwargs: Passed to fetch()

        Returns:
            VAST XML string
        """
        vast_params = params or {}

        if user_id:
            vast_params["uid"] = user_id
        if ip_address:
            vast_params["ip"] = ip_address
        if url:
            vast_params["url"] = url

        return await self.fetch(params=vast_params, context=context, **kwargs)


class VmapUpstream(VastUpstream):
    """
    VMAP (Video Multiple Ad Playlist) upstream.

    VMAP is used for ad pod scheduling across multiple ad breaks.
    Returns VMAP XML containing multiple VAST responses.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize VMAP upstream."""
        super().__init__(*args, **kwargs)
        # VMAP-specific configuration can be added here
