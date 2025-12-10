"""VAST protocol implementation."""

from xsp.protocols.vast.handler import VastProtocolHandler
from xsp.protocols.vast.chain import (
    ResolutionStrategy,
    SelectionStrategy,
    VastChainConfig,
)
from xsp.protocols.vast.chain_resolver import VastChainResolver
from xsp.protocols.vast.config_loader import VastChainConfigLoader
from xsp.protocols.vast.macros import MacroSubstitutor
from xsp.protocols.vast.types import (
    MediaType,
    VastResolutionResult,
    VastResponse,
    VastVersion,
)
from xsp.protocols.vast.upstream import VastUpstream, VmapUpstream
from xsp.protocols.vast.validation import VastValidationError, validate_vast_xml

__all__ = [
    "VastProtocolHandler",
    "MacroSubstitutor",
    "MediaType",
    "ResolutionStrategy",
    "SelectionStrategy",
    "VastChainConfig",
    "VastChainConfigLoader",
    "VastChainResolver",
    "VastResolutionResult",
    "VastResponse",
    "VastUpstream",
    "VastValidationError",
    "VastVersion",
    "VmapUpstream",
    "validate_vast_xml",
]
