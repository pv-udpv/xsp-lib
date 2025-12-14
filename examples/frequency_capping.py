"""Frequency capping middleware demonstration.

This example shows how to implement frequency capping for ad delivery
to control user experience and campaign effectiveness per IAB QAG guidelines.

Usage:
    python -m examples.frequency_capping

Demonstrates:
1. Per-user frequency capping (global)
2. Per-campaign frequency capping
3. InMemoryFrequencyStore usage
4. FrequencyCapExceeded error handling
5. Multiple user scenarios
6. IAB QAG compliance patterns

References:
    - IAB Quality Assurance Guidelines (QAG): Frequency capping recommendations
    - IAB Digital Video Ad Serving Template (VAST): Best practices
    - Typical frequency caps: 3-10 impressions per 24 hours
"""

import asyncio
from datetime import datetime

from xsp.core.exceptions import FrequencyCapExceeded
from xsp.core.session import SessionContext, VastSession
from xsp.middleware.base import MiddlewareStack
from xsp.middleware.frequency import FrequencyCap, FrequencyCappingMiddleware, InMemoryFrequencyStore
from xsp.protocols.vast import VastUpstream, VastVersion
from xsp.transports.memory import MemoryTransport


# Sample VAST XML for demonstration
SAMPLE_VAST = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="freq-demo-001">
        <InLine>
            <AdSystem>FreqCapDemo</AdSystem>
            <AdTitle>Frequency Capping Example</AdTitle>
            <Impression><![CDATA[https://tracking.example.com/imp]]></Impression>
            <Creatives>
                <Creative>
                    <Linear>
                        <Duration>00:00:30</Duration>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4">
                                <![CDATA[https://cdn.example.com/ad.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""


async def demo_global_frequency_cap():
    """
    Demonstrate global per-user frequency capping.

    Per IAB QAG recommendations, limit ad impressions to 3 per 24 hours
    to balance reach and user experience.
    """
    print("\n" + "=" * 70)
    print("DEMO 1: Global Per-User Frequency Capping")
    print("=" * 70)
    print("\nScenario: Limit each user to 3 impressions per 24 hours (IAB QAG)")
    print("-" * 70)

    # Create VAST upstream
    transport = MemoryTransport(SAMPLE_VAST.encode("utf-8"))
    vast_upstream = VastUpstream(
        transport=transport, endpoint="memory://global", version=VastVersion.V4_2
    )

    # Configure frequency capping: 3 impressions per 24 hours
    frequency_store = InMemoryFrequencyStore()
    frequency_cap = FrequencyCap(
        max_impressions=3,
        time_window_seconds=86400,  # 24 hours
        per_campaign=False,  # Global per-user (not per-campaign)
    )

    # Create middleware and wrap upstream
    freq_middleware = FrequencyCappingMiddleware(frequency_cap, frequency_store)
    middleware_stack = MiddlewareStack(freq_middleware)
    wrapped_upstream = middleware_stack.wrap(vast_upstream)

    print(f"Configuration:")
    print(f"  - Max impressions: {frequency_cap.max_impressions}")
    print(f"  - Time window: {frequency_cap.time_window_seconds}s (24 hours)")
    print(f"  - Per campaign: {frequency_cap.per_campaign}\n")

    # Test user-alice: Should succeed 3 times, fail on 4th
    print("Testing user-alice (should see exactly 3 ads):")
    print("-" * 70)

    for i in range(1, 6):
        try:
            ctx = SessionContext(
                request_id=f"req-global-alice-{i}",
                user_id="user-alice",
                ip_address="10.0.0.1",
                timestamp=datetime.now(),
            )
            session = VastSession(wrapped_upstream, ctx)

            print(f"Request {i}: ", end="")
            vast_xml = await session.fetch(params={"w": "640", "h": "480"})
            print(f"✓ Success (fetched {len(vast_xml)} bytes)")

            # Show current count
            current_count = await frequency_store.get_count("freq:user:user-alice")
            print(f"           Impression count: {current_count}/{frequency_cap.max_impressions}")

            await session.close()

        except FrequencyCapExceeded as e:
            print(f"✗ Blocked - Frequency cap exceeded")
            print(f"           {e}")
            break

    # Test different user - should have separate cap
    print("\nTesting user-bob (different user, separate cap):")
    print("-" * 70)

    for i in range(1, 3):
        try:
            ctx = SessionContext(
                request_id=f"req-global-bob-{i}",
                user_id="user-bob",
                ip_address="10.0.0.2",
                timestamp=datetime.now(),
            )
            session = VastSession(wrapped_upstream, ctx)

            print(f"Request {i}: ", end="")
            vast_xml = await session.fetch(params={"w": "640", "h": "480"})
            print(f"✓ Success (fetched {len(vast_xml)} bytes)")

            current_count = await frequency_store.get_count("freq:user:user-bob")
            print(f"           Impression count: {current_count}/{frequency_cap.max_impressions}")

            await session.close()

        except FrequencyCapExceeded as e:
            print(f"✗ Blocked - {e}")
            break

    # Summary
    print("\n" + "-" * 70)
    alice_final = await frequency_store.get_count("freq:user:user-alice")
    bob_final = await frequency_store.get_count("freq:user:user-bob")
    print(f"Summary:")
    print(f"  user-alice: {alice_final}/{frequency_cap.max_impressions} impressions")
    print(f"  user-bob: {bob_final}/{frequency_cap.max_impressions} impressions")
    print(f"  ✓ Each user has independent frequency cap")

    await vast_upstream.close()


async def demo_per_campaign_frequency_cap():
    """
    Demonstrate per-campaign frequency capping.

    Allow different frequency limits for different campaigns.
    Example: User can see 5 impressions per campaign per day.
    """
    print("\n" + "=" * 70)
    print("DEMO 2: Per-Campaign Frequency Capping")
    print("=" * 70)
    print("\nScenario: Limit to 5 impressions per campaign per user per day")
    print("-" * 70)

    # Create VAST upstream
    transport = MemoryTransport(SAMPLE_VAST.encode("utf-8"))
    vast_upstream = VastUpstream(
        transport=transport, endpoint="memory://campaign", version=VastVersion.V4_2
    )

    # Configure per-campaign frequency capping
    frequency_store = InMemoryFrequencyStore()
    frequency_cap = FrequencyCap(
        max_impressions=5,
        time_window_seconds=86400,  # 24 hours
        per_campaign=True,  # Enable per-campaign tracking
    )

    freq_middleware = FrequencyCappingMiddleware(frequency_cap, frequency_store)
    middleware_stack = MiddlewareStack(freq_middleware)
    wrapped_upstream = middleware_stack.wrap(vast_upstream)

    print(f"Configuration:")
    print(f"  - Max impressions: {frequency_cap.max_impressions}")
    print(f"  - Time window: {frequency_cap.time_window_seconds}s (24 hours)")
    print(f"  - Per campaign: {frequency_cap.per_campaign} (enabled)\n")

    # Test user-carol with campaign-A
    print("User user-carol, Campaign A:")
    print("-" * 70)

    for i in range(1, 4):
        try:
            ctx = SessionContext(
                request_id=f"req-carol-campA-{i}",
                user_id="user-carol",
                ip_address="10.0.0.3",
                timestamp=datetime.now(),
                metadata={"campaign_id": "campaign-A"},
            )
            session = VastSession(wrapped_upstream, ctx)

            print(f"Request {i}: ", end="")
            await session.fetch(
                params={"w": "1920", "h": "1080"}, campaign_id="campaign-A"
            )
            print(f"✓ Success (Campaign A)")

            count = await frequency_store.get_count("freq:user:user-carol:campaign:campaign-A")
            print(f"           Campaign A count: {count}/{frequency_cap.max_impressions}")

            await session.close()

        except FrequencyCapExceeded as e:
            print(f"✗ Blocked - {e}")
            break

    # Same user, different campaign - separate cap!
    print("\nUser user-carol, Campaign B (same user, different campaign):")
    print("-" * 70)

    for i in range(1, 4):
        try:
            ctx = SessionContext(
                request_id=f"req-carol-campB-{i}",
                user_id="user-carol",
                ip_address="10.0.0.3",
                timestamp=datetime.now(),
                metadata={"campaign_id": "campaign-B"},
            )
            session = VastSession(wrapped_upstream, ctx)

            print(f"Request {i}: ", end="")
            await session.fetch(
                params={"w": "1920", "h": "1080"}, campaign_id="campaign-B"
            )
            print(f"✓ Success (Campaign B)")

            count = await frequency_store.get_count("freq:user:user-carol:campaign:campaign-B")
            print(f"           Campaign B count: {count}/{frequency_cap.max_impressions}")

            await session.close()

        except FrequencyCapExceeded as e:
            print(f"✗ Blocked - {e}")
            break

    # Summary
    print("\n" + "-" * 70)
    campA_count = await frequency_store.get_count("freq:user:user-carol:campaign:campaign-A")
    campB_count = await frequency_store.get_count("freq:user:user-carol:campaign:campaign-B")
    print(f"Summary for user-carol:")
    print(f"  Campaign A: {campA_count}/{frequency_cap.max_impressions} impressions")
    print(f"  Campaign B: {campB_count}/{frequency_cap.max_impressions} impressions")
    print(f"  ✓ Same user can see different campaigns independently")

    await vast_upstream.close()


async def demo_frequency_cap_reset():
    """
    Demonstrate manual frequency cap reset.

    Useful for testing or administrative operations.
    """
    print("\n" + "=" * 70)
    print("DEMO 3: Frequency Cap Reset")
    print("=" * 70)
    print("\nScenario: Manual reset of user frequency cap")
    print("-" * 70)

    # Create simple setup
    frequency_store = InMemoryFrequencyStore()
    frequency_cap = FrequencyCap(max_impressions=2, time_window_seconds=3600, per_campaign=False)

    # Simulate 2 impressions
    print("Simulating 2 impressions for user-dave...")
    await frequency_store.increment("freq:user:user-dave", 3600)
    await frequency_store.increment("freq:user:user-dave", 3600)

    count_before = await frequency_store.get_count("freq:user:user-dave")
    print(f"  Impression count: {count_before}/{frequency_cap.max_impressions}")
    print(f"  Status: {'✗ CAPPED' if count_before >= frequency_cap.max_impressions else '✓ OK'}")

    # Reset
    print("\nResetting frequency cap for user-dave...")
    await frequency_store.reset("freq:user:user-dave")

    count_after = await frequency_store.get_count("freq:user:user-dave")
    print(f"  Impression count: {count_after}/{frequency_cap.max_impressions}")
    print(f"  Status: {'✗ CAPPED' if count_after >= frequency_cap.max_impressions else '✓ OK'}")
    print(f"  ✓ Frequency cap reset successfully")


async def demo_iab_qag_compliance():
    """
    Demonstrate IAB QAG compliance patterns.

    IAB QAG recommends:
    - 3-10 impressions per 24 hours for video ads
    - Progressive frequency capping (stricter over time)
    - User experience prioritization
    """
    print("\n" + "=" * 70)
    print("DEMO 4: IAB QAG Compliance Patterns")
    print("=" * 70)
    print("\nIAB QAG Recommendations:")
    print("  - Video ads: 3-10 impressions per 24 hours")
    print("  - Balance reach vs. user experience")
    print("  - Consider content type and user context")
    print("-" * 70)

    # Create different caps for different scenarios
    frequency_store = InMemoryFrequencyStore()

    # Standard video ad cap (per IAB QAG)
    video_cap = FrequencyCap(max_impressions=5, time_window_seconds=86400, per_campaign=False)

    # Stricter cap for interstitial/pre-roll
    interstitial_cap = FrequencyCap(max_impressions=3, time_window_seconds=86400, per_campaign=False)

    print("\nRecommended caps:")
    print(f"  Video ads (standard): {video_cap.max_impressions} per 24h")
    print(f"  Interstitial/pre-roll: {interstitial_cap.max_impressions} per 24h")

    # Simulate standard video
    print("\nSimulating standard video ad delivery:")
    for i in range(1, 6):
        count = await frequency_store.increment("freq:user:user-eve:standard", 86400)
        status = "✓" if count <= video_cap.max_impressions else "✗"
        print(f"  Impression {i}: {status} ({count}/{video_cap.max_impressions})")

    # Simulate interstitial
    print("\nSimulating interstitial ad delivery (stricter):")
    for i in range(1, 5):
        count = await frequency_store.increment("freq:user:user-eve:interstitial", 86400)
        status = "✓" if count <= interstitial_cap.max_impressions else "✗"
        print(f"  Impression {i}: {status} ({count}/{interstitial_cap.max_impressions})")

    print("\n" + "-" * 70)
    print("Best Practices:")
    print("  ✓ Use stricter caps for intrusive ad formats")
    print("  ✓ Consider user context and content type")
    print("  ✓ Monitor user engagement and adjust caps accordingly")
    print("  ✓ Provide opt-out mechanisms per privacy regulations")


async def main() -> None:
    """Run all frequency capping demonstrations."""
    print("\n" + "=" * 70)
    print("XSP-Lib Frequency Capping Middleware Examples")
    print("=" * 70)

    # Run all demos
    await demo_global_frequency_cap()
    await demo_per_campaign_frequency_cap()
    await demo_frequency_cap_reset()
    await demo_iab_qag_compliance()

    print("\n" + "=" * 70)
    print("All demonstrations complete!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. Frequency capping protects user experience")
    print("  2. Per-campaign caps allow flexible campaign management")
    print("  3. IAB QAG recommends 3-10 impressions per 24h for video")
    print("  4. InMemoryFrequencyStore is thread-safe for concurrent access")
    print("  5. FrequencyCapExceeded is raised when limits are hit")
    print("\nFor production use, replace InMemoryFrequencyStore with Redis")
    print("to support distributed deployments.\n")


if __name__ == "__main__":
    asyncio.run(main())
