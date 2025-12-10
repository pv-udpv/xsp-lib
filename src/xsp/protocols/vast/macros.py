"""IAB macro substitution for VAST URLs."""

import time
import random
from typing import Callable
from urllib.parse import quote
from dataclasses import dataclass

from .types import VastVersion


@dataclass
class MacroDefinition:
    """VAST macro definition with version info."""

    name: str
    provider: Callable[[], str] | None
    intro_version: VastVersion
    deprec_version: VastVersion | None = None
    ssai_recommended: bool = False


class MacroSubstitutor:
    """
    IAB standard macro substitution for VAST URLs.

    Supports:
    - Built-in macros: [TIMESTAMP], [CACHEBUSTING]
    - Context macros: [CONTENTPLAYHEAD], [ASSETURI], [ERRORCODE]
    - Version filtering: only macros compatible with current VAST version
    - SSAI mode: only SSAI-recommended macros
    """

    # Macro registry with version info
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
            provider=None,  # Context-based
            intro_version=VastVersion.V3_0,
            ssai_recommended=True,
        ),
        "SERVERUA": MacroDefinition(
            name="SERVERUA",
            provider=None,  # Context-based
            intro_version=VastVersion.V4_1,
            ssai_recommended=True,
        ),
        "ASSETURI": MacroDefinition(
            name="ASSETURI",
            provider=None,  # Context-based
            intro_version=VastVersion.V2_0,
            ssai_recommended=False,
        ),
        "ERRORCODE": MacroDefinition(
            name="ERRORCODE",
            provider=None,  # Context-based
            intro_version=VastVersion.V2_0,
            ssai_recommended=False,
        ),
    }

    def __init__(
        self,
        version: VastVersion = VastVersion.V4_2,
        ssai_mode: bool = False,
    ):
        """
        Initialize macro substitutor.

        Args:
            version: VAST version to filter macros by
            ssai_mode: If True, only use SSAI-recommended macros
        """
        self.version = version
        self.ssai_mode = ssai_mode
        self.custom_providers: dict[str, Callable[[], str]] = {}

    def register(
        self,
        macro: str,
        provider: Callable[[], str],
        ssai_recommended: bool = False,
    ) -> None:
        """
        Register custom macro provider.

        Args:
            macro: Macro name (without brackets)
            provider: Function returning macro value
            ssai_recommended: Whether macro is SSAI-recommended
        """
        if self.ssai_mode and not ssai_recommended:
            return  # Skip non-SSAI macros in SSAI mode

        self.custom_providers[macro.upper()] = provider

    def substitute(
        self,
        url: str,
        context: dict[str, str] | None = None,
    ) -> str:
        """
        Substitute macros in URL.

        Args:
            url: URL with macros like [TIMESTAMP], [CONTENTPLAYHEAD]
            context: Additional context values (playhead, error code, etc.)

        Returns:
            URL with macros replaced and URL-encoded
        """
        result = url

        # Built-in macros from registry
        for macro_def in self.MACRO_REGISTRY.values():
            # Version filtering
            if not self._is_macro_compatible(macro_def):
                continue

            # SSAI filtering
            if self.ssai_mode and not macro_def.ssai_recommended:
                continue

            pattern = f"[{macro_def.name}]"
            if pattern in result:
                if macro_def.provider:
                    value = macro_def.provider()
                    result = result.replace(pattern, quote(value, safe=""))
                elif context and macro_def.name.lower() in context:
                    value = str(context[macro_def.name.lower()])
                    result = result.replace(pattern, quote(value, safe=""))

        # Custom macros
        for macro, provider in self.custom_providers.items():
            pattern = f"[{macro}]"
            if pattern in result:
                value = provider()
                result = result.replace(pattern, quote(value, safe=""))

        # Context macros (fallback for non-registered)
        if context:
            for key, value in context.items():
                pattern = f"[{key.upper()}]"
                if pattern in result:
                    result = result.replace(pattern, quote(str(value), safe=""))

        return result

    def _is_macro_compatible(self, macro_def: MacroDefinition) -> bool:
        """
        Check if macro is compatible with current VAST version.

        Args:
            macro_def: Macro definition

        Returns:
            True if macro can be used with current version
        """
        # Check introduction version
        version_order = [
            VastVersion.V2_0,
            VastVersion.V3_0,
            VastVersion.V4_0,
            VastVersion.V4_1,
            VastVersion.V4_2,
        ]

        current_idx = version_order.index(self.version)
        intro_idx = version_order.index(macro_def.intro_version)

        if intro_idx > current_idx:
            return False  # Macro not yet introduced

        # Check deprecation
        if macro_def.deprec_version:
            deprec_idx = version_order.index(macro_def.deprec_version)
            if deprec_idx <= current_idx:
                return False  # Macro deprecated

        return True
