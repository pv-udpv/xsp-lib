"""Tests for middleware system."""

import pytest

from xsp.core.base import BaseUpstream
from xsp.core.exceptions import UpstreamError
from xsp.middleware.base import MiddlewareStack
from xsp.middleware.retry import RetryMiddleware
from xsp.transports.memory import MemoryTransport


class FailingTransport:
    """Transport that fails a configurable number of times."""

    def __init__(self, fail_count: int, response: bytes):
        self.fail_count = fail_count
        self.response = response
        self.attempts = 0

    @property
    def transport_type(self):
        from xsp.core.transport import TransportType

        return TransportType.MEMORY

    async def send(self, **kwargs):
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise UpstreamError(f"Attempt {self.attempts} failed")
        return self.response

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_retry_middleware_success():
    """Test retry middleware with successful retry."""
    transport = FailingTransport(fail_count=2, response=b"success")
    upstream = BaseUpstream(
        transport=transport, decoder=lambda b: b.decode("utf-8"), endpoint="test"
    )

    middleware = MiddlewareStack(RetryMiddleware(max_attempts=3, backoff_base=0.1))
    wrapped = middleware.wrap(upstream)

    result = await wrapped.fetch()
    assert result == "success"
    assert transport.attempts == 3


@pytest.mark.asyncio
async def test_retry_middleware_exhausted():
    """Test retry middleware with exhausted retries."""
    transport = FailingTransport(fail_count=5, response=b"success")
    upstream = BaseUpstream(
        transport=transport, decoder=lambda b: b.decode("utf-8"), endpoint="test"
    )

    middleware = MiddlewareStack(RetryMiddleware(max_attempts=3, backoff_base=0.1))
    wrapped = middleware.wrap(upstream)

    with pytest.raises(UpstreamError):
        await wrapped.fetch()

    assert transport.attempts == 3


@pytest.mark.asyncio
async def test_middleware_stack_no_middleware():
    """Test middleware stack with no middleware."""
    transport = MemoryTransport(b"test")
    upstream = BaseUpstream(
        transport=transport, decoder=lambda b: b.decode("utf-8"), endpoint="test"
    )

    middleware = MiddlewareStack()
    wrapped = middleware.wrap(upstream)

    result = await wrapped.fetch()
    assert result == "test"
