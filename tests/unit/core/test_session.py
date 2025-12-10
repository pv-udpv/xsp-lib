"""Tests for session abstractions."""

import pytest
from dataclasses import FrozenInstanceError

from xsp.core.session import SessionContext


def test_session_context_immutable() -> None:
    """SessionContext should be immutable."""
    context = SessionContext(
        timestamp=123456789,
        correlator="abc",
        cachebusting="xyz",
        cookies={},
        request_id="req-1",
    )

    with pytest.raises(FrozenInstanceError):
        context.timestamp = 999  # type: ignore[misc]


def test_session_context_creation() -> None:
    """SessionContext should store all fields."""
    context = SessionContext(
        timestamp=123456789,
        correlator="session-abc",
        cachebusting="rand-xyz",
        cookies={"uid": "user123"},
        request_id="req-001",
    )

    assert context.timestamp == 123456789
    assert context.correlator == "session-abc"
    assert context.cachebusting == "rand-xyz"
    assert context.cookies == {"uid": "user123"}
    assert context.request_id == "req-001"
