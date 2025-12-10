"""Tests for middleware system."""

import pytest

from xsp.core.base import BaseUpstream
from xsp.core.exceptions import TransportError, UpstreamError
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

    with pytest.raises(TransportError):
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


class RecordingUpstream:
    """Upstream that records kwargs passed to fetch."""

    def __init__(self):
        self.received_kwargs: dict | None = None

    async def fetch(self, **kwargs):  # type: ignore[override]
        self.received_kwargs = kwargs
        return kwargs

    async def close(self):
        pass

    async def health_check(self):
        return True


class ModifyKwargsMiddleware:
    """Middleware that adds and overrides kwargs before upstream call."""

    async def __call__(self, upstream, next_handler, **kwargs):  # type: ignore[override]
        new_params = {"added": "value", **(kwargs.get("params") or {})}
        new_kwargs = {**kwargs, "params": new_params, "override": "middleware"}
        return await next_handler(**new_kwargs)


@pytest.mark.asyncio
async def test_middleware_can_modify_kwargs():
    """Middleware should be able to adjust kwargs before reaching upstream."""

    upstream = RecordingUpstream()
    middleware = MiddlewareStack(ModifyKwargsMiddleware())
    wrapped = middleware.wrap(upstream)

    result = await wrapped.fetch(params={"initial": True}, override="original")

    assert result == {
        "params": {"added": "value", "initial": True},
        "override": "middleware",
    }
    assert upstream.received_kwargs == result


@pytest.mark.asyncio
async def test_multiple_middleware_kwargs_merging():
    """Test that kwargs are correctly merged through multiple middleware in the chain."""

    class AddKeyMiddleware:
        """Middleware that adds a specified key-value pair to kwargs."""

        def __init__(self, key: str, value: str):
            self.key = key
            self.value = value

        async def __call__(self, upstream, next_handler, **kwargs):  # type: ignore[override]
            new_kwargs = {**kwargs, self.key: self.value}
            return await next_handler(**new_kwargs)

    upstream = RecordingUpstream()
    # Create stack with two middleware that each add different keys
    middleware = MiddlewareStack(
        AddKeyMiddleware("key1", "from_middleware_a"),
        AddKeyMiddleware("key2", "from_middleware_b"),
    )
    wrapped = middleware.wrap(upstream)

    result = await wrapped.fetch(initial_param="original")

    # Both key1 (from first middleware) and key2 (from second middleware)
    # should reach the upstream
    assert result == {
        "initial_param": "original",
        "key1": "from_middleware_a",
        "key2": "from_middleware_b",
    }
    assert upstream.received_kwargs == result
