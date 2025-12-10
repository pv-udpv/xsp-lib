"""Tests for state backend implementations."""

import pytest

from xsp.core.state import InMemoryStateBackend


@pytest.mark.asyncio
async def test_in_memory_state_backend_get_set() -> None:
    """Test basic get/set operations."""
    backend = InMemoryStateBackend()

    # Set a value
    await backend.set("key1", "value1")

    # Get the value
    result = await backend.get("key1")
    assert result == "value1"

    await backend.close()


@pytest.mark.asyncio
async def test_in_memory_state_backend_get_nonexistent() -> None:
    """Test getting a non-existent key."""
    backend = InMemoryStateBackend()

    result = await backend.get("nonexistent")
    assert result is None

    await backend.close()


@pytest.mark.asyncio
async def test_in_memory_state_backend_exists() -> None:
    """Test key existence check."""
    backend = InMemoryStateBackend()

    await backend.set("key1", "value1")

    assert await backend.exists("key1") is True
    assert await backend.exists("nonexistent") is False

    await backend.close()


@pytest.mark.asyncio
async def test_in_memory_state_backend_delete() -> None:
    """Test key deletion."""
    backend = InMemoryStateBackend()

    await backend.set("key1", "value1")
    assert await backend.exists("key1") is True

    await backend.delete("key1")
    assert await backend.exists("key1") is False
    assert await backend.get("key1") is None

    await backend.close()


@pytest.mark.asyncio
async def test_in_memory_state_backend_close() -> None:
    """Test closing backend clears data."""
    backend = InMemoryStateBackend()

    await backend.set("key1", "value1")
    await backend.set("key2", "value2")

    await backend.close()

    # After close, store should be cleared
    assert await backend.get("key1") is None
    assert await backend.get("key2") is None


@pytest.mark.asyncio
async def test_in_memory_state_backend_complex_values() -> None:
    """Test storing complex values."""
    backend = InMemoryStateBackend()

    # Store dict
    await backend.set("dict_key", {"a": 1, "b": 2})
    result = await backend.get("dict_key")
    assert result == {"a": 1, "b": 2}

    # Store list
    await backend.set("list_key", [1, 2, 3])
    result = await backend.get("list_key")
    assert result == [1, 2, 3]

    await backend.close()
