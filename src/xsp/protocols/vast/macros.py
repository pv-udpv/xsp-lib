"""IAB standard macro substitution for VAST URLs."""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote

from .types import VastVersion


@dataclass
class MacroDefinition:
    name: str
    provider: Callable[[], str] | None
    intro_version: VastVersion
    deprec_version: VastVersion | None = None
    ssai_recommended: bool = False


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

    MACRO_REGISTRY: dict[str, MacroDefinition] = {
        "TIMESTAMP": MacroDefinition(
            name="TIMESTAMP",
            provider=lambda: str(int(time.time() * 1000)),
            intro_version=VastVersion.V2_0,
            ssai_recommended=True,
        ),
        "CACHEBUSTING": MacroDefinition(
            name="CACHEBUSTING",
            provider=lambda: str(random.randint(100000000, 999999999)),
            intro_version=VastVersion.V2_0,
            ssai_recommended=True,
        ),
        "CONTENTPLAYHEAD": MacroDefinition(
            name="CONTENTPLAYHEAD",
            provider=None,
            intro_version=VastVersion.V3_0,
            ssai_recommended=True,
        ),
        "SERVERUA": MacroDefinition(
            name="SERVERUA",
            provider=None,
            intro_version=VastVersion.V4_0,
            ssai_recommended=True,
        ),
    }

    def __init__(
        self, version: VastVersion = VastVersion.V4_2, ssai_mode: bool = False
    ) -> None:
        """Initialize with built-in macro providers."""
        self.version = version
        self.ssai_mode = ssai_mode
        self.providers: dict[str, Callable[[], str]] = {}

        # Register built-in macros that are compatible with version
        for macro_name, macro_def in self.MACRO_REGISTRY.items():
            if macro_def.provider and self._is_macro_compatible(macro_def):
                self.providers[macro_name] = macro_def.provider

    def _is_macro_compatible(self, macro_def: MacroDefinition) -> bool:
        """
        Check if macro is compatible with current version and SSAI mode.

        Args:
            macro_def: Macro definition to check

        Returns:
            True if macro is compatible
        """
        # Check version compatibility
        if macro_def.intro_version.value > self.version.value:
            return False

        if macro_def.deprec_version and macro_def.deprec_version.value <= self.version.value:
            return False

        # Check SSAI mode compatibility
        if self.ssai_mode and not macro_def.ssai_recommended:
            return False

        return True

    def register(
        self, macro: str, provider: Callable[[], str], ssai_recommended: bool = False
    ) -> None:
        """
        Register custom macro provider.

        Args:
            macro: Macro name (without brackets, e.g., "CUSTOM")
            provider: Function returning macro value
            ssai_recommended: Whether macro is recommended for SSAI mode
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

        # Built-in macros (filtered by version and SSAI mode)
        for macro, provider in self.providers.items():
            pattern = f"[{macro}]"
            if pattern in result:
                value = provider()
                # Use safe chars appropriate for query params
                result = result.replace(pattern, quote(value, safe="-_.~"))

        # Context macros (with version filtering)
        if context:
            for key, value in context.items():
                macro_name = key.upper()
                pattern = f"[{macro_name}]"
                if pattern in result:
                    # Check if this is a known macro that needs version filtering
                    if macro_name in self.MACRO_REGISTRY:
                        macro_def = self.MACRO_REGISTRY[macro_name]
                        if not self._is_macro_compatible(macro_def):
                            continue
                    # Use safe chars appropriate for query params
                    result = result.replace(pattern, quote(str(value), safe="-_.~"))

        return result
