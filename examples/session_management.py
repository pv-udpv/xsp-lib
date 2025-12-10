"""Session Management Example.

This example demonstrates complete session management with xsp-lib, including:
- Creating session contexts
- Starting and managing sessions
- Making session-aware requests
- Updating session state
- Proper cleanup and resource management

For production use, replace MemoryBackend with RedisBackend.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from xsp.core.base import BaseUpstream
from xsp.core.exceptions import XspError
from xsp.transports.memory import MemoryTransport


# ============================================================================
# Session Context (Immutable)
# ============================================================================


@dataclass(frozen=True)
class SessionContext:
    """Immutable session context for ad requests.

    The frozen=True parameter ensures immutability - once created,
    the context cannot be modified. This prevents bugs from
    unintended mutations and enables safe sharing across async tasks.

    Attributes:
        session_id: Unique session identifier (UUID recommended)
        user_id: User identifier for frequency capping and personalization
        device_id: Device identifier (IDFA, Android ID, etc.)
        ip_address: Client IP address for geo-targeting
        user_agent: User agent string for device detection
        content_url: URL of content where ad will be shown
        metadata: Additional session metadata (arbitrary key-value pairs)
    """

    session_id: str
    user_id: str | None = None
    device_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    content_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_metadata(self, **kwargs: Any) -> "SessionContext":
        """Create new context with updated metadata.

        Since SessionContext is immutable, this method creates a new
        instance with the specified metadata keys added/updated.

        Args:
            **kwargs: Metadata keys to add or update

        Returns:
            New SessionContext with updated metadata
        """
        from dataclasses import replace

        merged_metadata = {**self.metadata, **kwargs}
        return replace(self, metadata=merged_metadata)


# ============================================================================
# State Backend (In-Memory for Testing)
# ============================================================================


class MemoryBackend:
    """In-memory state backend for testing.

    For production, use RedisBackend or DynamoDBBackend instead.
    """

    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float | None]] = {}

    async def get(self, key: str) -> Any | None:
        """Get value, checking expiration."""
        if key not in self._data:
            return None

        value, expires_at = self._data[key]

        # Check if expired
        if expires_at is not None and time.time() > expires_at:
            del self._data[key]
            return None

        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value with optional TTL in seconds."""
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl

        self._data[key] = (value, expires_at)

    async def increment(self, key: str, delta: int = 1) -> int:
        """Atomically increment counter."""
        current = await self.get(key)
        if current is None:
            current = 0

        new_value = current + delta
        await self.set(key, new_value)
        return new_value

    async def delete(self, key: str) -> None:
        """Delete key."""
        self._data.pop(key, None)

    def clear(self) -> None:
        """Clear all data (testing utility)."""
        self._data.clear()


# ============================================================================
# Session Upstream Implementation
# ============================================================================


class SessionUpstream(BaseUpstream[str]):
    """Upstream with session management support.

    Extends BaseUpstream to add session state tracking and persistence.
    """

    def __init__(
        self,
        *args: Any,
        state_backend: MemoryBackend | None = None,
        **kwargs: Any,
    ):
        """Initialize session upstream.

        Args:
            *args: Passed to BaseUpstream
            state_backend: Optional state backend for persistence
            **kwargs: Passed to BaseUpstream
        """
        super().__init__(*args, **kwargs)
        self.state_backend = state_backend
        self._context: SessionContext | None = None
        self._session_state: dict[str, Any] = {}

    async def start_session(self, context: SessionContext) -> None:
        """Initialize session with context.

        Args:
            context: Immutable session context

        Raises:
            XspError: If session already started
        """
        if self._context is not None:
            raise XspError("Session already started")

        self._context = context
        self._session_state = {"request_count": 0, "created_at": time.time()}

        # Load persisted state if backend available
        if self.state_backend:
            key = f"session:{context.session_id}"
            persisted = await self.state_backend.get(key)
            if persisted:
                print(f"  Loaded persisted state for session {context.session_id[:8]}...")
                self._session_state = persisted

    async def fetch_with_session(
        self,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Fetch using session state.

        Args:
            params: Request-specific parameters
            headers: Request-specific headers

        Returns:
            Response data as string

        Raises:
            XspError: If session not started
        """
        if self._context is None:
            raise XspError("Session not started - call start_session() first")

        # Merge session context into params
        merged_params = params or {}
        if self._context.user_id:
            merged_params["user_id"] = self._context.user_id
        if self._context.device_id:
            merged_params["device_id"] = self._context.device_id

        # Add session metadata to params
        for key, value in self._context.metadata.items():
            if key not in merged_params:
                merged_params[key] = value

        # Use parent fetch
        result = await self.fetch(params=merged_params, headers=headers)

        # Update session state
        self._session_state["request_count"] = (
            self._session_state.get("request_count", 0) + 1
        )
        self._session_state["last_request_time"] = time.time()

        # Persist if backend available
        if self.state_backend and self._context:
            key = f"session:{self._context.session_id}"
            await self.state_backend.set(key, self._session_state, ttl=3600)

        return result

    async def update_session_state(self, state: dict[str, Any]) -> None:
        """Update session state.

        Args:
            state: State updates to apply

        Raises:
            XspError: If session not started
        """
        if self._context is None:
            raise XspError("Session not started")

        self._session_state.update(state)

        # Persist if backend available
        if self.state_backend:
            key = f"session:{self._context.session_id}"
            await self.state_backend.set(key, self._session_state, ttl=3600)

    async def get_session_state(self) -> dict[str, Any]:
        """Get current session state.

        Returns:
            Current mutable session state (copy)
        """
        return self._session_state.copy()

    async def end_session(self) -> None:
        """Clean up session resources.

        Persists final state with longer TTL and releases resources.
        """
        if self.state_backend and self._context:
            # Final state persist with 24h TTL
            key = f"session:{self._context.session_id}"
            self._session_state["ended_at"] = time.time()
            await self.state_backend.set(key, self._session_state, ttl=86400)
            print(f"  Persisted final state for session {self._context.session_id[:8]}...")

        self._context = None
        self._session_state = {}

        await self.close()


# ============================================================================
# Example 1: Basic Session
# ============================================================================


async def example_basic_session() -> None:
    """Demonstrate basic session creation and usage."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Session")
    print("=" * 70 + "\n")

    # Mock VAST response
    mock_vast = b"""<?xml version="1.0"?>
<VAST version="4.2">
    <Ad id="basic123">
        <InLine>
            <AdTitle>Basic Session Ad</AdTitle>
        </InLine>
    </Ad>
</VAST>"""

    # Create upstream
    upstream = SessionUpstream(
        transport=MemoryTransport(mock_vast),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
    )

    # Create session context
    context = SessionContext(
        session_id=str(uuid4()), user_id="user_12345", device_id="IDFA-ABC-123"
    )

    print(f"Created session: {context.session_id[:8]}...")
    print(f"User: {context.user_id}, Device: {context.device_id}\n")

    # Start session
    await upstream.start_session(context)

    try:
        # Make request
        result = await upstream.fetch_with_session(params={"w": "640", "h": "480"})
        print(f"Fetched ad ({len(result)} bytes)")
        print(f"Ad title: {result[result.find('<AdTitle>'):result.find('</AdTitle>') + 10]}\n")

        # Check state
        state = await upstream.get_session_state()
        print(f"Session state:")
        print(f"  Request count: {state['request_count']}")
        print(f"  Created at: {state['created_at']:.2f}")

    finally:
        # Always clean up
        await upstream.end_session()
        print("\nSession ended\n")


# ============================================================================
# Example 2: Session with State Updates
# ============================================================================


async def example_session_with_state_updates() -> None:
    """Demonstrate explicit state updates."""
    print("\n" + "=" * 70)
    print("Example 2: Session with State Updates")
    print("=" * 70 + "\n")

    mock_vast = b"<VAST version='4.2'><Ad id='123'><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"

    upstream = SessionUpstream(
        transport=MemoryTransport(mock_vast),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
    )

    context = SessionContext(
        session_id=str(uuid4()),
        user_id="user_67890",
        metadata={"placement": "pre-roll", "content_id": "video_123"},
    )

    await upstream.start_session(context)

    try:
        # Make multiple requests
        print("Making 3 ad requests...\n")
        for i in range(3):
            await upstream.fetch_with_session(params={"position": str(i + 1)})
            print(f"  Request {i + 1} completed")

        # Update state after impressions
        print("\nRecording impressions and watch time...\n")
        await upstream.update_session_state(
            {
                "impressions_shown": 3,
                "total_watch_time_seconds": 90,
                "last_impression_time": time.time(),
            }
        )

        # Get final state
        state = await upstream.get_session_state()
        print("Final session state:")
        for key, value in state.items():
            if key.endswith("_time"):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")

    finally:
        await upstream.end_session()
        print("\nSession ended\n")


# ============================================================================
# Example 3: Session with Persistence
# ============================================================================


async def example_session_with_persistence() -> None:
    """Demonstrate session state persistence across instances."""
    print("\n" + "=" * 70)
    print("Example 3: Session with Persistence")
    print("=" * 70 + "\n")

    # Shared backend
    backend = MemoryBackend()
    mock_vast = b"<VAST version='4.2'><Ad><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"

    # Create session ID that will be reused
    session_id = str(uuid4())
    print(f"Using persistent session: {session_id[:8]}...\n")

    # First session: create and update state
    print("First upstream instance:")
    upstream1 = SessionUpstream(
        transport=MemoryTransport(mock_vast),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
        state_backend=backend,
    )

    context = SessionContext(session_id=session_id, user_id="persistent_user")

    await upstream1.start_session(context)
    await upstream1.fetch_with_session()
    await upstream1.fetch_with_session()
    await upstream1.update_session_state({"impressions": 2, "custom_field": "test"})

    state1 = await upstream1.get_session_state()
    print(f"  Requests made: {state1['request_count']}")
    print(f"  Impressions: {state1['impressions']}")
    await upstream1.end_session()

    print("\nSecond upstream instance (loading persisted state):")

    # Second session: load persisted state
    upstream2 = SessionUpstream(
        transport=MemoryTransport(mock_vast),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
        state_backend=backend,
    )

    await upstream2.start_session(context)

    # State should be loaded from backend
    state2 = await upstream2.get_session_state()
    print(f"  Loaded request count: {state2['request_count']} (from first instance)")
    print(f"  Loaded impressions: {state2['impressions']} (from first instance)")
    print(f"  Loaded custom field: {state2['custom_field']}")

    # Make additional request
    await upstream2.fetch_with_session()
    state3 = await upstream2.get_session_state()
    print(f"  New request count: {state3['request_count']} (incremented)")

    await upstream2.end_session()
    print("\nSession ended\n")


# ============================================================================
# Example 4: Multiple Sessions
# ============================================================================


async def example_multiple_sessions() -> None:
    """Demonstrate managing multiple concurrent sessions."""
    print("\n" + "=" * 70)
    print("Example 4: Multiple Concurrent Sessions")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    mock_vast = b"<VAST><Ad><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"

    async def run_user_session(user_id: str, request_count: int) -> dict[str, Any]:
        """Run a session for a single user."""
        upstream = SessionUpstream(
            transport=MemoryTransport(mock_vast),
            decoder=lambda b: b.decode("utf-8"),
            endpoint="memory://vast",
            state_backend=backend,
        )

        context = SessionContext(
            session_id=str(uuid4()), user_id=user_id, metadata={"source": "concurrent"}
        )

        await upstream.start_session(context)

        try:
            for _ in range(request_count):
                await upstream.fetch_with_session()

            state = await upstream.get_session_state()
            return {"user_id": user_id, "requests": state["request_count"]}

        finally:
            await upstream.end_session()

    # Run 5 concurrent user sessions
    print("Starting 5 concurrent user sessions...\n")

    tasks = [
        run_user_session(f"user_{i}", i + 1) for i in range(5)  # Each user makes different number of requests
    ]

    results = await asyncio.gather(*tasks)

    print("Session results:")
    for result in results:
        print(f"  {result['user_id']}: {result['requests']} requests")

    print("\n")


# ============================================================================
# Example 5: Complete Lifecycle
# ============================================================================


async def example_complete_lifecycle() -> None:
    """Demonstrate complete session lifecycle with all phases."""
    print("\n" + "=" * 70)
    print("Example 5: Complete Session Lifecycle")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    mock_vast = b"<VAST><Ad><InLine><AdTitle>Lifecycle Ad</AdTitle></InLine></Ad></VAST>"

    upstream = SessionUpstream(
        transport=MemoryTransport(mock_vast),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
        state_backend=backend,
    )

    context = SessionContext(
        session_id=str(uuid4()),
        user_id="lifecycle_user",
        device_id="IDFA-LIFECYCLE",
        ip_address="203.0.113.42",
        metadata={"placement": "pre-roll", "content_duration": 600},
    )

    # Phase 1: Creation
    print("Phase 1: Creating session")
    print(f"  Session ID: {context.session_id[:8]}...")
    print(f"  User ID: {context.user_id}")
    print(f"  Placement: {context.metadata['placement']}")
    await upstream.start_session(context)
    print("  ✓ Session started\n")

    try:
        # Phase 2: Requests
        print("Phase 2: Making requests")
        for i in range(3):
            await upstream.fetch_with_session(params={"position": str(i + 1)})
            print(f"  ✓ Request {i + 1} completed")

        state = await upstream.get_session_state()
        print(f"  Total requests: {state['request_count']}\n")

        # Phase 3: State Updates
        print("Phase 3: Updating state")
        await upstream.update_session_state(
            {
                "impressions_shown": 3,
                "completion_rate": 0.85,
                "total_watch_time": 72,
                "campaign_ids_shown": ["camp_1", "camp_2", "camp_3"],
            }
        )
        print("  ✓ State updated with impressions and metrics\n")

        # Display final state
        final_state = await upstream.get_session_state()
        print("Final state:")
        for key, value in final_state.items():
            if key.endswith("_time"):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")

    finally:
        # Phase 4: Cleanup
        print("\nPhase 4: Cleanup")
        await upstream.end_session()
        print("  ✓ Session ended and state persisted\n")


# ============================================================================
# Main
# ============================================================================


async def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 70)
    print("XSP-LIB SESSION MANAGEMENT EXAMPLES")
    print("=" * 70)

    await example_basic_session()
    await example_session_with_state_updates()
    await example_session_with_persistence()
    await example_multiple_sessions()
    await example_complete_lifecycle()

    print("=" * 70)
    print("All examples completed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
