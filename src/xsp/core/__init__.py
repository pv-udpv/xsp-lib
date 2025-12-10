"""Core abstractions."""

from xsp.core.base import BaseUpstream
from xsp.core.dialer import Dialer, HttpDialer
from xsp.core.exceptions import (
    DecodeError,
    TransportError,
    UpstreamError,
    UpstreamTimeout,
    ValidationError,
    XspError,
)
from xsp.core.transport import Transport, TransportType
from xsp.core.types import Context, Headers, Metadata, Params
from xsp.core.upstream import Upstream

__all__ = [
    "BaseUpstream",
    "Context",
    "DecodeError",
    "Dialer",
    "Headers",
    "HttpDialer",
    "Metadata",
    "Params",
    "Transport",
    "TransportError",
    "TransportType",
    "Upstream",
    "UpstreamError",
    "UpstreamTimeout",
    "ValidationError",
    "XspError",
]
