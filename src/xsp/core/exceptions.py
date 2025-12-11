"""Core exceptions for xsp-lib."""


class XspError(Exception):
    """Base exception for xsp-lib."""


class UpstreamError(XspError):
    """Upstream operation failed."""


class TransportError(XspError):
    """Transport layer error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class TransportTimeoutError(TransportError):
    """Request timed out."""


class TransportConnectionError(TransportError):
    """Connection failed."""


class UpstreamTimeout(UpstreamError):  # noqa: N818
    """Upstream request timed out."""


class DecodeError(UpstreamError):
    """Failed to decode response."""


class ValidationError(XspError):
    """Schema validation failed."""


class FrequencyCapExceeded(XspError):  # noqa: N818
    """Frequency cap limit exceeded."""


class BudgetExceeded(XspError):  # noqa: N818
    """Budget limit exceeded."""
