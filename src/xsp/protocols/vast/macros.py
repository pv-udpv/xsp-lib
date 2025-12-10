"""IAB standard macro substitution for VAST URLs."""

import random
import time
from collections.abc import Callable
from urllib.parse import quote

from xsp.core.configurable import configurable


@configurable(
    namespace="vast.macros",
    description="IAB macro substitution configuration",
)
class MacroSubstitutor:
    """
    IAB standard macro substitution for VAST URLs.

    Supports built-in macros:
    - [TIMESTAMP] - Unix timestamp in milliseconds
    - [CACHEBUSTING] - Random 9-digit number
    - [CONTENTPLAYHEAD] - Video playback position (from context)
    - [ASSETURI] - Creative asset URI (from context)
    - [ERRORCODE] - VAST error code (from context)

    Plus custom macros via registration.
    """

    def __init__(
        self,
        *,
        enable_cachebusting: bool = True,
        enable_timestamp: bool = True,
    ) -> None:
        """
        Initialize with built-in macro providers.

        Args:
            enable_cachebusting: Enable [CACHEBUSTING] macro
            enable_timestamp: Enable [TIMESTAMP] macro
        """
        self.providers: dict[str, Callable[[], str]] = {}

        if enable_timestamp:
            self.providers["TIMESTAMP"] = lambda: str(int(time.time() * 1000))

        if enable_cachebusting:
            self.providers["CACHEBUSTING"] = lambda: str(random.randint(100000000, 999999999))

    def register(self, macro: str, provider: Callable[[], str]) -> None:
        """
        Register custom macro provider.

        Args:
            macro: Macro name (without brackets, e.g., "CUSTOM")
            provider: Function returning macro value
        """
        self.providers[macro.upper()] = provider

    def substitute(self, url: str, context: dict[str, str] | None = None) -> str:
        """
        Substitute macros in URL.

        Args:
            url: URL with macros like [TIMESTAMP], [CONTENTPLAYHEAD]
            context: Additional context values (playhead, error code, etc.)

        Returns:
            URL with macros replaced and URL-encoded
        """
        result = url

        # Built-in macros
        for macro, provider in self.providers.items():
            pattern = f"[{macro}]"
            if pattern in result:
                value = provider()
                # Use safe chars appropriate for query params
                result = result.replace(pattern, quote(value, safe="-_.~"))

        # Context macros
        if context:
            for key, value in context.items():
                pattern = f"[{key.upper()}]"
                if pattern in result:
                    # Use safe chars appropriate for query params
                    result = result.replace(pattern, quote(str(value), safe="-_.~"))

        return result
