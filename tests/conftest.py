"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_response_text() -> bytes:
    """Sample text response for testing."""
    return b"test response"


@pytest.fixture
def sample_response_json() -> bytes:
    """Sample JSON response for testing."""
    return b'{"key": "value", "number": 42}'
