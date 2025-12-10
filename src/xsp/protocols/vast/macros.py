"""IAB macro substitution for VAST URLs."""

import time
import random
from typing import Callable, Any
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
        
        # Pre-filter macros based on version and SSAI mode for performance
        self._filtered_macros: dict[str, MacroDefinition] = {}
        for name, macro_def in self.MACRO_REGISTRY.items():
            if self._is_macro_compatible(macro_def):
                if not ssai_mode or macro_def.ssai_recommended:
                    self._filtered_macros[name] = macro_def

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
        context: dict[str, Any] | None = None,
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
        
        # Normalize context keys to lowercase for case-insensitive lookup
        normalized_context: dict[str, Any] = {}
        if context:
            normalized_context = {k.lower(): v for k, v in context.items()}

        # Built-in macros from pre-filtered registry
        for macro_def in self._filtered_macros.values():
            pattern = f"[{macro_def.name}]"
            if pattern in result:
                if macro_def.provider:
                    value = macro_def.provider()
                    result = result.replace(pattern, quote(value, safe="-_.~"))
                elif macro_def.name.lower() in normalized_context:
                    value = str(normalized_context[macro_def.name.lower()])
                    result = result.replace(pattern, quote(value, safe="-_.~"))

        # Custom macros
        for macro, provider in self.custom_providers.items():
            pattern = f"[{macro}]"
            if pattern in result:
                value = provider()
                result = result.replace(pattern, quote(value, safe="-_.~"))

        # Context macros (fallback for non-registered macros only)
        for key, value in normalized_context.items():
            pattern = f"[{key.upper()}]"
            if pattern in result and self._should_substitute_context_macro(key.upper()):
                result = result.replace(pattern, quote(str(value), safe="-_.~"))

        return result

    def _should_substitute_context_macro(self, macro_name: str) -> bool:
        """
        Check if a context macro should be substituted.
        
        Args:
            macro_name: Uppercase macro name
            
        Returns:
            True if the macro should be substituted
            
        Rules:
            - Registered macros: only substitute if they passed version/SSAI filtering
            - Context-only macros: always substitute if not registered
        """
        # If registered, check if it passed filtering
        if macro_name in self.MACRO_REGISTRY:
            return macro_name in self._filtered_macros
        # Context-only macros are always substituted
        return True

    def _is_macro_compatible(self, macro_def: MacroDefinition) -> bool:
        """
        Check if macro is compatible with current VAST version.

        Args:
            macro_def: Macro definition

        Returns:
            True if macro can be used with current version
        """
        # per VAST 4.2 §3.5: Macro is available if introduced in or before current version,
        # and not deprecated in or before current version.
        if self.version < macro_def.intro_version:
            return False  # Macro not yet introduced

        if macro_def.deprec_version is not None and self.version >= macro_def.deprec_version:
            return False  # Macro deprecated

        return True
