"""Core exceptions."""


class XspError(Exception):
    """Base exception for xsp-lib."""


class UpstreamError(XspError):
    """Upstream operation failed."""


class TransportError(XspError):
    """Transport layer error."""

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize transport error with optional status code."""
        super().__init__(message)
        self.status_code = status_code


class TransportTimeoutError(TransportError):
    """Request timed out.
    
    This exception never has a status code.
    """

    def __init__(self, message: str) -> None:
        """Initialize timeout error (never has a status code)."""
        super().__init__(message, status_code=None)


class TransportConnectionError(TransportError):
    """Connection failed.
    
    This exception never has a status code.
    """

    def __init__(self, message: str) -> None:
        """Initialize connection error (never has a status code)."""
        super().__init__(message, status_code=None)


class UpstreamTimeout(UpstreamError):
    """Upstream request timed out."""


class DecodeError(UpstreamError):
    """Failed to decode response."""


class ValidationError(XspError):
    """Schema validation failed."""


# VAST-specific exceptions
class VastError(UpstreamError):
    """VAST protocol error."""


class VastTimeoutError(VastError):
    """VAST request timed out."""


class VastNetworkError(VastError):
    """VAST network error."""


class VastHttpError(VastError):
    """VAST HTTP error."""

    def __init__(self, message: str, status_code: int):
        """Initialize VAST HTTP error with status code."""
        super().__init__(message)
        self.status_code = status_code


class VastParseError(VastError):
    """VAST XML parsing error."""
