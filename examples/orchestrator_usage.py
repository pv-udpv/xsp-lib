"""Complete orchestration example showing Phase 4 features.

This example demonstrates a realistic ad serving workflow using:
- HttpDialer for connection pooling
- VastSession for state tracking
- FrequencyCappingMiddleware for impression limits
- BudgetTrackingMiddleware for spend control
- Proper error handling and configuration best practices

Usage:
    python -m examples.orchestrator_usage

Example demonstrates:
1. Setting up HttpDialer with optimized connection pooling
2. Creating VAST upstream with session tracking
3. Applying frequency capping (3 impressions per 24 hours)
4. Applying budget tracking ($1000 USD campaign budget)
5. Making ad requests for multiple users
6. Handling FrequencyCapExceeded and BudgetExceeded errors
7. Proper resource cleanup

References:
    - IAB VAST 4.2: https://iabtechlab.com/vast
    - IAB QAG: Frequency capping best practices
    - OpenRTB 2.6: Budget signaling in programmatic advertising
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from xsp.core.dialer import HttpDialer
from xsp.core.exceptions import BudgetExceeded, FrequencyCapExceeded
from xsp.core.session import SessionContext, VastSession
from xsp.middleware.base import MiddlewareStack
from xsp.middleware.budget import Budget, BudgetTrackingMiddleware, InMemoryBudgetStore
from xsp.middleware.frequency import FrequencyCap, FrequencyCappingMiddleware, InMemoryFrequencyStore
from xsp.protocols.vast import VastUpstream, VastVersion
from xsp.transports.http import HttpTransport


async def main() -> None:
    """
    Demonstrate complete Phase 4 orchestration workflow.

    This example shows production-ready configuration for:
    - Connection pooling for high-traffic scenarios
    - Session-based request tracking
    - User frequency capping per IAB QAG recommendations
    - Campaign budget enforcement with Decimal precision
    - Comprehensive error handling
    """
    print("=== XSP-Lib Phase 4 Orchestration Example ===\n")

    # Step 1: Configure HttpDialer with connection pooling
    # For high-traffic ad serving, configure larger pools to handle concurrent requests
    print("1. Configuring HttpDialer with connection pooling...")
    dialer = HttpDialer(
        pool_limits={
            "max_connections": 200,  # Total concurrent connections
            "max_keepalive_connections": 50,  # Idle keepalive connections
        },
        timeout=15.0,  # Aggressive timeout for ad serving
    )
    print(f"   ✓ Connection pool configured (max: 200, keepalive: 50)\n")

    # Step 2: Create VAST upstream with HTTP transport
    # Using memory transport for demo - replace with real endpoint in production
    print("2. Creating VAST upstream...")

    # Sample VAST XML for demonstration
    # In production, this would come from an actual ad server
    sample_vast = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="demo-12345">
        <InLine>
            <AdSystem>DemoAdServer</AdSystem>
            <AdTitle>Phase 4 Demo Advertisement</AdTitle>
            <Impression><![CDATA[https://tracking.example.com/imp?id=12345]]></Impression>
            <Creatives>
                <Creative>
                    <Linear>
                        <Duration>00:00:15</Duration>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1920" height="1080">
                                <![CDATA[https://cdn.example.com/video.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""

    # Note: Using memory transport for demo. In production, use:
    # transport = HttpTransport()
    # vast_upstream = VastUpstream(
    #     transport=transport,
    #     endpoint="https://your-ad-server.com/vast",
    #     version=VastVersion.V4_2,
    # )
    from xsp.transports.memory import MemoryTransport

    vast_upstream = VastUpstream(
        transport=MemoryTransport(sample_vast.encode("utf-8")),
        endpoint="memory://demo",
        version=VastVersion.V4_2,
    )
    print(f"   ✓ VAST upstream created (endpoint: memory://demo)\n")

    # Step 3: Configure frequency capping middleware
    # Per IAB QAG recommendations: 3-10 impressions per 24 hours
    print("3. Configuring frequency capping (3 impressions per 24 hours)...")
    frequency_store = InMemoryFrequencyStore()
    frequency_cap = FrequencyCap(
        max_impressions=3,
        time_window_seconds=86400,  # 24 hours
        per_campaign=False,  # Global per-user cap
    )
    freq_middleware = FrequencyCappingMiddleware(frequency_cap, frequency_store)
    print(f"   ✓ Frequency cap configured: {frequency_cap.max_impressions} impressions/24h\n")

    # Step 4: Configure budget tracking middleware
    # Campaign budget: $1000 USD with $2.50 cost per impression (CPM-like pricing)
    print("4. Configuring budget tracking ($1000 USD campaign)...")
    budget_store = InMemoryBudgetStore()

    # Initialize campaign budget
    campaign_budget = Budget(
        total_budget=Decimal("1000.00"),
        spent=Decimal("0.00"),
        currency="USD",
        campaign_id="campaign-demo-2024",
    )
    budget_store._store["budget:campaign:campaign-demo-2024"] = campaign_budget

    budget_middleware = BudgetTrackingMiddleware(
        store=budget_store,
        default_cost=Decimal("2.50"),  # $2.50 per impression
        per_campaign=True,
    )
    print(f"   ✓ Budget configured: ${campaign_budget.total_budget} USD\n")
    print(f"   ✓ Cost per impression: $2.50 USD\n")

    # Step 5: Build middleware stack
    # Order matters: frequency cap first, then budget check
    # This prevents budget charges for frequency-capped users
    print("5. Building middleware stack...")
    middleware_stack = MiddlewareStack(
        freq_middleware,  # Check frequency cap first
        budget_middleware,  # Then check budget
    )
    wrapped_upstream = middleware_stack.wrap(vast_upstream)
    print("   ✓ Middleware stack: FrequencyCapping → BudgetTracking → VAST\n")

    # Step 6: Simulate ad requests for multiple users
    print("6. Simulating ad serving workflow...\n")
    print("=" * 70)

    # User 1: Normal flow - will hit frequency cap
    print("\nUser 1 (user-alice): Testing frequency cap enforcement")
    print("-" * 70)

    for i in range(1, 5):
        try:
            # Create session context for each request
            ctx = SessionContext(
                request_id=f"req-alice-{i}",
                user_id="user-alice",
                ip_address="192.168.1.100",
                timestamp=datetime.now(),
                metadata={
                    "campaign_id": "campaign-demo-2024",
                    "device": "desktop",
                    "platform": "web",
                },
            )

            # Wrap in VastSession for state tracking
            session = VastSession(wrapped_upstream, ctx)

            # Make request
            print(f"  Request {i}: Fetching VAST for user-alice...")
            vast_xml = await session.fetch(
                params={"w": "1920", "h": "1080"},
                campaign_id="campaign-demo-2024",
                cost=Decimal("2.50"),
            )
            print(f"  ✓ Success! Fetched {len(vast_xml)} bytes")
            print(f"    Session state: {session.state['request_count']} requests")

            # Check current budget
            current_budget = await budget_store.get_budget("budget:campaign:campaign-demo-2024")
            remaining = current_budget.total_budget - current_budget.spent
            print(f"    Budget: ${current_budget.spent} / ${current_budget.total_budget}")
            print(f"    Remaining: ${remaining}\n")

            await session.close()

        except FrequencyCapExceeded as e:
            print(f"  ✗ Frequency cap exceeded!")
            print(f"    Error: {e}\n")
            break
        except BudgetExceeded as e:
            print(f"  ✗ Budget exceeded!")
            print(f"    Error: {e}\n")
            break

    # User 2: Different user - separate frequency cap
    print("\nUser 2 (user-bob): Testing separate frequency cap")
    print("-" * 70)

    for i in range(1, 3):
        try:
            ctx = SessionContext(
                request_id=f"req-bob-{i}",
                user_id="user-bob",
                ip_address="192.168.1.101",
                timestamp=datetime.now(),
                metadata={
                    "campaign_id": "campaign-demo-2024",
                    "device": "mobile",
                    "platform": "ios",
                },
            )

            session = VastSession(wrapped_upstream, ctx)

            print(f"  Request {i}: Fetching VAST for user-bob...")
            vast_xml = await session.fetch(
                params={"w": "640", "h": "480"},
                campaign_id="campaign-demo-2024",
                cost=Decimal("2.50"),
            )
            print(f"  ✓ Success! Fetched {len(vast_xml)} bytes")
            print(f"    Session state: {session.state['request_count']} requests\n")

            await session.close()

        except (FrequencyCapExceeded, BudgetExceeded) as e:
            print(f"  ✗ Request blocked: {e}\n")
            break

    # Step 7: Display final statistics
    print("=" * 70)
    print("\n7. Final Statistics:")
    print("-" * 70)

    # Frequency cap statistics
    alice_count = await frequency_store.get_count("freq:user:user-alice")
    bob_count = await frequency_store.get_count("freq:user:user-bob")
    print(f"  Frequency caps:")
    print(f"    user-alice: {alice_count}/{frequency_cap.max_impressions} impressions")
    print(f"    user-bob: {bob_count}/{frequency_cap.max_impressions} impressions")

    # Budget statistics
    final_budget = await budget_store.get_budget("budget:campaign:campaign-demo-2024")
    if final_budget:
        remaining = final_budget.total_budget - final_budget.spent
        utilization = (final_budget.spent / final_budget.total_budget) * Decimal("100")
        print(f"\n  Campaign budget:")
        print(f"    Total: ${final_budget.total_budget} {final_budget.currency}")
        print(f"    Spent: ${final_budget.spent} {final_budget.currency}")
        print(f"    Remaining: ${remaining} {final_budget.currency}")
        print(f"    Utilization: {utilization:.1f}%")

    print("\n" + "=" * 70)

    # Step 8: Cleanup
    print("\n8. Cleaning up resources...")
    await vast_upstream.close()
    await dialer.close()
    print("   ✓ Resources released\n")

    print("=== Example Complete ===\n")


if __name__ == "__main__":
    # Run the orchestration demo
    asyncio.run(main())
