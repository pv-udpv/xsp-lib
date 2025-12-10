"""VAST protocol implementation."""

from xsp.protocols.vast.chain import (
    ResolutionStrategy,
    SelectionStrategy,
    VastChainConfig,
)
from xsp.protocols.vast.chain_resolver import VastChainResolver
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
    "MacroSubstitutor",
    "MediaType",
    "ResolutionStrategy",
    "SelectionStrategy",
    "VastChainConfig",
    "VastChainResolver",
    "VastResolutionResult",
    "VastResponse",
    "VastUpstream",
    "VastValidationError",
    "VastVersion",
    "VmapUpstream",
    "validate_vast_xml",
]
