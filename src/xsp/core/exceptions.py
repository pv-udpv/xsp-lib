"""Core exceptions for xsp-lib."""


class XspError(Exception):
    """Base exception for xsp-lib."""


class UpstreamError(XspError):
    """Upstream operation failed."""


class TransportError(XspError):
    """Transport layer error."""


class UpstreamTimeout(UpstreamError):
    """Upstream request timed out."""


class DecodeError(UpstreamError):
    """Failed to decode response."""


class ValidationError(XspError):
    """Schema validation failed."""
