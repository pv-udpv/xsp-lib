"""Upstream service protocol."""

from typing import Any, Protocol, TypeVar

T = TypeVar("T", covariant=True)


class Upstream(Protocol[T]):
    """
    Universal upstream service protocol.

    Represents any AdTech service: VAST ad servers, OpenRTB bidders,
    DAAST audio servers, analytics endpoints, etc.
    """

    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> T:
        """Fetch data from upstream."""
        ...

    async def close(self) -> None:
        """Release resources."""
        ...

    async def health_check(self) -> bool:
        """Check upstream health."""
        ...
