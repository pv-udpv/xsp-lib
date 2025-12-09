"""Middleware base protocol and stack."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from xsp.core.upstream import Upstream

FetchFunc = Callable[..., Awaitable[Any]]


class Middleware(Protocol):
    """Middleware for upstream requests."""

    async def __call__(
        self, upstream: Upstream[Any], next_handler: FetchFunc, **kwargs: Any
    ) -> Any:
        """
        Process request through middleware.

        Args:
            upstream: The upstream instance
            next_handler: Next handler in the chain
            **kwargs: Request arguments

        Returns:
            Response from upstream
        """
        ...


class MiddlewareWrappedUpstream:
    """Upstream wrapped with middleware stack."""

    def __init__(self, upstream: Upstream[Any], middleware: list[Middleware]):
        """
        Initialize wrapped upstream.

        Args:
            upstream: Base upstream instance
            middleware: List of middleware to apply
        """
        self._upstream = upstream
        self._middleware = middleware

    async def fetch(self, **kwargs: Any) -> Any:
        """Fetch through middleware chain."""

        async def create_handler(index: int) -> Any:
            if index >= len(self._middleware):
                # End of chain, call actual upstream
                return await self._upstream.fetch(**kwargs)

            middleware = self._middleware[index]

            async def next_handler(**inner_kwargs: Any) -> Any:
                # Continue chain
                return await create_handler(index + 1)

            return await middleware(self._upstream, next_handler, **kwargs)

        return await create_handler(0)

    async def close(self) -> None:
        """Close underlying upstream."""
        await self._upstream.close()

    async def health_check(self) -> bool:
        """Check underlying upstream health."""
        return await self._upstream.health_check()


class MiddlewareStack:
    """Compose multiple middleware."""

    def __init__(self, *middleware: Middleware):
        """
        Initialize middleware stack.

        Args:
            *middleware: Middleware instances to apply in order
        """
        self.middleware = list(middleware)

    def wrap(self, upstream: Upstream[Any]) -> MiddlewareWrappedUpstream:
        """
        Wrap upstream with middleware.

        Args:
            upstream: Upstream to wrap

        Returns:
            Wrapped upstream with middleware applied
        """
        return MiddlewareWrappedUpstream(upstream, self.middleware)
