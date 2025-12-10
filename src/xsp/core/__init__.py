"""Core abstractions."""

from xsp.core.base import BaseUpstream
from xsp.core.config import UpstreamConfig
from xsp.core.exceptions import (
    DecodeError,
    TransportError,
    UpstreamError,
    UpstreamTimeout,
    ValidationError,
    XspError,
)
from xsp.core.protocol import AdRequest, AdResponse, ProtocolHandler
from xsp.core.state import InMemoryStateBackend, RedisStateBackend, StateBackend
from xsp.core.transport import Transport, TransportType
from xsp.core.types import Context, Headers, Metadata, Params
from xsp.core.upstream import Upstream

__all__ = [
    "AdRequest",
    "AdResponse",
    "BaseUpstream",
    "Context",
    "DecodeError",
    "Headers",
    "InMemoryStateBackend",
    "Metadata",
    "Params",
    "ProtocolHandler",
    "RedisStateBackend",
    "StateBackend",
    "Transport",
    "TransportError",
    "TransportType",
    "Upstream",
    "UpstreamConfig",
    "UpstreamError",
    "UpstreamTimeout",
    "ValidationError",
    "XspError",
]
