"""Frequency Capping Example.

This example demonstrates frequency capping implementation with xsp-lib:
- Limiting impressions per user/campaign
- Time-based windows (hourly, daily, lifetime)
- Multiple cap rules
- Integration with session management

Frequency capping prevents ad fatigue by limiting how often users see
the same ad or campaign, improving user experience and campaign performance.
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
# Exceptions
# ============================================================================


class FrequencyCapExceeded(XspError):
    """Raised when frequency cap is exceeded."""

    pass


# ============================================================================
# Session Context
# ============================================================================


@dataclass(frozen=True)
class SessionContext:
    """Immutable session context."""

    session_id: str
    user_id: str | None = None
    device_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# State Backend
# ============================================================================


class MemoryBackend:
    """In-memory state backend for testing."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float | None]] = {}

    async def get(self, key: str) -> Any | None:
        """Get value, checking expiration."""
        if key not in self._data:
            return None

        value, expires_at = self._data[key]

        if expires_at is not None and time.time() > expires_at:
            del self._data[key]
            return None

        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value with optional TTL."""
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

    def clear(self) -> None:
        """Clear all data."""
        self._data.clear()


# ============================================================================
# Frequency Capper
# ============================================================================


class FrequencyCapper:
    """Frequency capping enforcement using state backend.

    Supports:
    - Per-campaign caps
    - Per-creative caps
    - Time-based windows (hourly, daily, lifetime)
    - Multiple cap rules
    """

    def __init__(
        self,
        backend: MemoryBackend,
        default_cap: int = 3,
        window_seconds: int = 86400,  # 24 hours
    ):
        """Initialize frequency capper.

        Args:
            backend: State backend for persistence
            default_cap: Default maximum impressions
            window_seconds: Time window for cap (seconds)
        """
        self.backend = backend
        self.default_cap = default_cap
        self.window_seconds = window_seconds

    async def check_cap(
        self,
        user_id: str,
        campaign_id: str,
        max_impressions: int | None = None,
    ) -> bool:
        """Check if user has exceeded frequency cap.

        Args:
            user_id: User identifier
            campaign_id: Campaign identifier
            max_impressions: Override default cap

        Returns:
            True if under cap, False if cap exceeded
        """
        cap = max_impressions or self.default_cap
        key = self._make_key(user_id, campaign_id)

        count = await self.backend.get(key)
        if count is None:
            return True  # No impressions yet

        return count < cap

    async def record_impression(
        self,
        user_id: str,
        campaign_id: str,
    ) -> int:
        """Record impression and return new count.

        Args:
            user_id: User identifier
            campaign_id: Campaign identifier

        Returns:
            New impression count

        Raises:
            FrequencyCapExceeded: If recording would exceed cap
        """
        key = self._make_key(user_id, campaign_id)

        # Atomic increment
        new_count = await self.backend.increment(key)

        # Set TTL on first impression
        if new_count == 1:
            await self.backend.set(key, new_count, ttl=self.window_seconds)

        return new_count

    async def get_remaining(
        self,
        user_id: str,
        campaign_id: str,
        max_impressions: int | None = None,
    ) -> int:
        """Get remaining impressions before cap.

        Args:
            user_id: User identifier
            campaign_id: Campaign identifier
            max_impressions: Override default cap

        Returns:
            Remaining impressions (0 if cap exceeded)
        """
        cap = max_impressions or self.default_cap
        key = self._make_key(user_id, campaign_id)

        count = await self.backend.get(key) or 0
        remaining = cap - count
        return max(0, remaining)

    async def get_count(
        self,
        user_id: str,
        campaign_id: str,
    ) -> int:
        """Get current impression count.

        Args:
            user_id: User identifier
            campaign_id: Campaign identifier

        Returns:
            Current impression count
        """
        key = self._make_key(user_id, campaign_id)
        count = await self.backend.get(key)
        return count or 0

    def _make_key(self, user_id: str, campaign_id: str) -> str:
        """Generate cache key for frequency cap."""
        return f"freq_cap:{user_id}:{campaign_id}"


# ============================================================================
# Frequency-Capped Session Upstream
# ============================================================================


class FrequencyCappedSessionUpstream(BaseUpstream[str]):
    """Session upstream with frequency capping."""

    def __init__(
        self,
        *args: Any,
        frequency_capper: FrequencyCapper,
        state_backend: MemoryBackend | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.frequency_capper = frequency_capper
        self.state_backend = state_backend
        self._context: SessionContext | None = None
        self._session_state: dict[str, Any] = {}

    async def start_session(self, context: SessionContext) -> None:
        """Initialize session."""
        if self._context is not None:
            raise XspError("Session already started")

        self._context = context
        self._session_state = {"request_count": 0}

    async def fetch_with_session(
        self,
        campaign_id: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Fetch with frequency cap check.

        Args:
            campaign_id: Campaign identifier for frequency cap
            params: Request parameters
            **kwargs: Additional arguments

        Returns:
            Ad response

        Raises:
            XspError: If session not started or context missing user_id
            FrequencyCapExceeded: If frequency cap exceeded
        """
        if self._context is None:
            raise XspError("Session not started")

        if self._context.user_id is None:
            raise XspError("Session context missing user_id for frequency capping")

        # Check frequency cap
        can_serve = await self.frequency_capper.check_cap(
            user_id=self._context.user_id,
            campaign_id=campaign_id,
        )

        if not can_serve:
            count = await self.frequency_capper.get_count(
                self._context.user_id, campaign_id
            )
            raise FrequencyCapExceeded(
                f"User {self._context.user_id} exceeded cap for campaign {campaign_id} "
                f"(count: {count}, cap: {self.frequency_capper.default_cap})"
            )

        # Fetch ad
        result = await self.fetch(params=params, **kwargs)

        # Record impression
        new_count = await self.frequency_capper.record_impression(
            user_id=self._context.user_id,
            campaign_id=campaign_id,
        )

        # Update session state
        self._session_state["request_count"] = (
            self._session_state.get("request_count", 0) + 1
        )
        self._session_state[f"impressions_{campaign_id}"] = new_count

        return result

    async def get_session_state(self) -> dict[str, Any]:
        """Get current session state."""
        return self._session_state.copy()

    async def end_session(self) -> None:
        """Clean up session."""
        self._context = None
        self._session_state = {}
        await self.close()


# ============================================================================
# Example 1: Basic Frequency Capping
# ============================================================================


async def example_basic_frequency_cap() -> None:
    """Demonstrate basic frequency capping."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Frequency Capping")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    capper = FrequencyCapper(
        backend=backend,
        default_cap=3,  # Max 3 impressions
        window_seconds=86400,  # Per 24 hours
    )

    mock_ad = b"<VAST><Ad id='123'><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"

    upstream = FrequencyCappedSessionUpstream(
        transport=MemoryTransport(mock_ad),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
        frequency_capper=capper,
    )

    context = SessionContext(session_id=str(uuid4()), user_id="user_12345")

    await upstream.start_session(context)

    print(f"Frequency cap: {capper.default_cap} impressions per {capper.window_seconds // 3600} hours")
    print(f"User: {context.user_id}")
    print(f"Campaign: camp_1\n")

    try:
        # First 3 impressions succeed
        for i in range(3):
            try:
                ad = await upstream.fetch_with_session(campaign_id="camp_1")
                remaining = await capper.get_remaining(context.user_id, "camp_1")
                print(f"✓ Impression {i + 1} served (remaining: {remaining})")
            except FrequencyCapExceeded as e:
                print(f"✗ Impression {i + 1} blocked: {e}")

        # 4th impression fails
        print("\nAttempting 4th impression...")
        try:
            await upstream.fetch_with_session(campaign_id="camp_1")
            print("✗ Should have been blocked!")
        except FrequencyCapExceeded as e:
            print(f"✓ Correctly blocked: Frequency cap exceeded")

    finally:
        await upstream.end_session()

    print("\n")


# ============================================================================
# Example 2: Multiple Campaigns
# ============================================================================


async def example_multiple_campaigns() -> None:
    """Demonstrate frequency caps across multiple campaigns."""
    print("\n" + "=" * 70)
    print("Example 2: Multiple Campaigns with Different Caps")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    capper = FrequencyCapper(backend=backend, default_cap=5)

    mock_ad = b"<VAST><Ad><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"

    upstream = FrequencyCappedSessionUpstream(
        transport=MemoryTransport(mock_ad),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
        frequency_capper=capper,
    )

    context = SessionContext(session_id=str(uuid4()), user_id="user_67890")
    await upstream.start_session(context)

    campaigns = ["camp_automotive", "camp_retail", "camp_finance"]

    print("Serving ads from 3 different campaigns...\n")

    try:
        # Serve 2 impressions from each campaign
        for campaign_id in campaigns:
            print(f"Campaign: {campaign_id}")
            for i in range(2):
                await upstream.fetch_with_session(campaign_id=campaign_id)
                count = await capper.get_count(context.user_id, campaign_id)
                remaining = await capper.get_remaining(context.user_id, campaign_id)
                print(f"  Impression {i + 1}: count={count}, remaining={remaining}")

            print()

        # Show final state
        print("Final frequency cap status:")
        for campaign_id in campaigns:
            count = await capper.get_count(context.user_id, campaign_id)
            remaining = await capper.get_remaining(context.user_id, campaign_id)
            print(f"  {campaign_id}: {count}/{capper.default_cap} (remaining: {remaining})")

    finally:
        await upstream.end_session()

    print("\n")


# ============================================================================
# Example 3: Time Window Expiration
# ============================================================================


async def example_time_window_expiration() -> None:
    """Demonstrate frequency cap window expiration."""
    print("\n" + "=" * 70)
    print("Example 3: Time Window Expiration")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    capper = FrequencyCapper(
        backend=backend,
        default_cap=2,
        window_seconds=2,  # 2 second window for demo
    )

    mock_ad = b"<VAST><Ad><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"

    upstream = FrequencyCappedSessionUpstream(
        transport=MemoryTransport(mock_ad),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
        frequency_capper=capper,
    )

    context = SessionContext(session_id=str(uuid4()), user_id="user_timing")
    await upstream.start_session(context)

    print(f"Frequency cap: {capper.default_cap} impressions per {capper.window_seconds} seconds\n")

    try:
        # Serve 2 impressions (reach cap)
        print("Phase 1: Serving impressions (reaching cap)")
        for i in range(2):
            await upstream.fetch_with_session(campaign_id="camp_time")
            print(f"  ✓ Impression {i + 1} served")

        # Try 3rd (should fail)
        print("\nPhase 2: Attempting 3rd impression (should fail)")
        try:
            await upstream.fetch_with_session(campaign_id="camp_time")
            print("  ✗ Should have been blocked!")
        except FrequencyCapExceeded:
            print("  ✓ Correctly blocked by frequency cap")

        # Wait for window to expire
        print(f"\nPhase 3: Waiting {capper.window_seconds} seconds for window to expire...")
        await asyncio.sleep(capper.window_seconds + 0.1)

        # Try again (should succeed with fresh window)
        print("Phase 4: Attempting impression after expiration")
        await upstream.fetch_with_session(campaign_id="camp_time")
        count = await capper.get_count(context.user_id, "camp_time")
        print(f"  ✓ Impression served (new window, count: {count})")

    finally:
        await upstream.end_session()

    print("\n")


# ============================================================================
# Example 4: Custom Cap Per Campaign
# ============================================================================


async def example_custom_caps() -> None:
    """Demonstrate custom frequency caps per campaign."""
    print("\n" + "=" * 70)
    print("Example 4: Custom Caps Per Campaign")
    print("=" * 70 + "\n")

    backend = MemoryBackend()

    # Different cappers for different campaign types
    premium_capper = FrequencyCapper(backend=backend, default_cap=2)  # Premium: 2 per day
    standard_capper = FrequencyCapper(backend=backend, default_cap=5)  # Standard: 5 per day

    mock_ad = b"<VAST><Ad><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"

    user_id = "user_custom"
    session_id = str(uuid4())

    print("Campaign types with different frequency caps:")
    print("  Premium campaigns: 2 impressions/day")
    print("  Standard campaigns: 5 impressions/day\n")

    # Serve premium campaign (cap: 2)
    print("Serving premium campaign (cap: 2)")
    upstream_premium = FrequencyCappedSessionUpstream(
        transport=MemoryTransport(mock_ad),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
        frequency_capper=premium_capper,
    )

    context = SessionContext(session_id=session_id, user_id=user_id)
    await upstream_premium.start_session(context)

    try:
        for i in range(2):
            await upstream_premium.fetch_with_session(campaign_id="camp_premium")
            remaining = await premium_capper.get_remaining(user_id, "camp_premium")
            print(f"  Impression {i + 1}: remaining={remaining}")

        # Try 3rd (should fail)
        try:
            await upstream_premium.fetch_with_session(campaign_id="camp_premium")
            print("  ✗ Should have been blocked!")
        except FrequencyCapExceeded:
            print("  ✓ Cap reached, further impressions blocked\n")

    finally:
        await upstream_premium.end_session()

    # Serve standard campaign (cap: 5)
    print("Serving standard campaign (cap: 5)")
    upstream_standard = FrequencyCappedSessionUpstream(
        transport=MemoryTransport(mock_ad),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
        frequency_capper=standard_capper,
    )

    await upstream_standard.start_session(context)

    try:
        for i in range(5):
            await upstream_standard.fetch_with_session(campaign_id="camp_standard")
            remaining = await standard_capper.get_remaining(user_id, "camp_standard")
            print(f"  Impression {i + 1}: remaining={remaining}")

    finally:
        await upstream_standard.end_session()

    print("\n")


# ============================================================================
# Example 5: Production-Ready Frequency Capping
# ============================================================================


async def example_production_frequency_capping() -> None:
    """Demonstrate production-ready frequency capping with monitoring."""
    print("\n" + "=" * 70)
    print("Example 5: Production-Ready Frequency Capping")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    capper = FrequencyCapper(
        backend=backend,
        default_cap=3,
        window_seconds=86400,  # 24 hours
    )

    mock_ad = b"<VAST><Ad><InLine><AdTitle>Production Ad</AdTitle></InLine></Ad></VAST>"

    upstream = FrequencyCappedSessionUpstream(
        transport=MemoryTransport(mock_ad),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
        frequency_capper=capper,
        state_backend=backend,
    )

    # Simulate multiple user sessions
    users = ["user_001", "user_002", "user_003"]
    campaigns = ["camp_A", "camp_B"]

    print("Simulating production ad serving with frequency capping...\n")

    metrics = {
        "total_requests": 0,
        "ads_served": 0,
        "blocked_by_cap": 0,
    }

    for user_id in users:
        context = SessionContext(session_id=str(uuid4()), user_id=user_id)
        await upstream.start_session(context)

        print(f"User: {user_id}")

        try:
            # Each user requests ads from both campaigns
            for campaign_id in campaigns:
                for attempt in range(4):  # Try 4 times (cap is 3)
                    metrics["total_requests"] += 1

                    try:
                        await upstream.fetch_with_session(campaign_id=campaign_id)
                        metrics["ads_served"] += 1
                        count = await capper.get_count(user_id, campaign_id)
                        remaining = await capper.get_remaining(user_id, campaign_id)
                        print(
                            f"  {campaign_id} attempt {attempt + 1}: ✓ served (count={count}, remaining={remaining})"
                        )

                    except FrequencyCapExceeded:
                        metrics["blocked_by_cap"] += 1
                        print(f"  {campaign_id} attempt {attempt + 1}: ✗ blocked (cap exceeded)")

        finally:
            await upstream.end_session()

        print()

    # Display metrics
    print("=" * 70)
    print("Production Metrics Summary")
    print("=" * 70)
    print(f"Total requests: {metrics['total_requests']}")
    print(f"Ads served: {metrics['ads_served']}")
    print(f"Blocked by cap: {metrics['blocked_by_cap']}")
    print(
        f"Block rate: {metrics['blocked_by_cap'] / metrics['total_requests'] * 100:.1f}%"
    )
    print("\n")


# ============================================================================
# Main
# ============================================================================


async def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 70)
    print("XSP-LIB FREQUENCY CAPPING EXAMPLES")
    print("=" * 70)

    await example_basic_frequency_cap()
    await example_multiple_campaigns()
    await example_time_window_expiration()
    await example_custom_caps()
    await example_production_frequency_capping()

    print("=" * 70)
    print("All examples completed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
