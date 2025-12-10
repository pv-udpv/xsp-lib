"""VAST protocol implementation."""

from xsp.protocols.vast.handler import VastProtocolHandler
from xsp.protocols.vast.macros import MacroSubstitutor
from xsp.protocols.vast.types import MediaType, VastResponse, VastVersion
from xsp.protocols.vast.upstream import VastUpstream, VmapUpstream
from xsp.protocols.vast.validation import VastValidationError, validate_vast_xml

__all__ = [
    "VastProtocolHandler",
    "MacroSubstitutor",
    "MediaType",
    "VastResponse",
    "VastUpstream",
    "VastValidationError",
    "VastVersion",
    "VmapUpstream",
    "validate_vast_xml",
]
