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


class VastError(UpstreamError):
    """VAST protocol error."""


class VastTimeoutError(VastError):
    """VAST request timed out."""


class VastNetworkError(VastError):
    """VAST network error."""


class VastHttpError(VastError):
    """VAST HTTP error."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class VastParseError(VastError):
    """VAST XML parsing error."""


class OpenRTBError(UpstreamError):
    """OpenRTB protocol error."""


class OpenRTBTimeoutError(OpenRTBError):
    """OpenRTB request timed out."""


class OpenRTBNetworkError(OpenRTBError):
    """OpenRTB network error."""


class OpenRTBHttpError(OpenRTBError):
    """OpenRTB HTTP error."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class OpenRTBParseError(OpenRTBError):
    """OpenRTB JSON parsing error."""


class OpenRTBNoBidError(OpenRTBError):
    """No bid received from bidder."""
