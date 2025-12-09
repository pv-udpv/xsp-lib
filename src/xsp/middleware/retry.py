"""Retry middleware with exponential backoff."""

import asyncio
from typing import Any, Type

from xsp.core.exceptions import UpstreamError
from xsp.core.upstream import Upstream
from xsp.middleware.base import FetchFunc


class RetryMiddleware:
    """Retry with exponential backoff."""

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_base: float = 2.0,
        retriable_exceptions: tuple[Type[Exception], ...] = (UpstreamError,),
    ):
        """
        Initialize retry middleware.

        Args:
            max_attempts: Maximum number of retry attempts
            backoff_base: Base for exponential backoff (seconds)
            retriable_exceptions: Tuple of exception types to retry on
        """
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.retriable_exceptions = retriable_exceptions

    async def __call__(
        self, upstream: Upstream[Any], next_handler: FetchFunc, **kwargs: Any
    ) -> Any:
        """
        Execute request with retry logic.

        Args:
            upstream: Upstream instance
            next_handler: Next handler in chain
            **kwargs: Request arguments

        Returns:
            Response from upstream

        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return await next_handler(**kwargs)
            except self.retriable_exceptions as e:
                last_exception = e

                # Don't sleep after last attempt
                if attempt < self.max_attempts - 1:
                    delay = self.backoff_base**attempt
                    await asyncio.sleep(delay)

        # All retries exhausted, raise last exception
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("Retry failed without exception")
