"""Budget tracking middleware demonstration.

This example shows how to implement budget tracking and enforcement
for advertising campaigns with Decimal precision for financial accuracy.

Usage:
    python -m examples.budget_tracking

Demonstrates:
1. Campaign budget tracking with Decimal precision
2. Real-time spend updates
3. BudgetExceeded error handling
4. Multiple campaigns with different budgets
5. Cost calculation (CPM, CPC, direct cost)
6. Budget reset functionality

References:
    - IAB OpenRTB 2.6 §3.2.1: Budget signaling
    - IAB Programmatic Supply Chain: Budget pacing best practices
    - Industry standards: Decimal for financial precision
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from xsp.core.exceptions import BudgetExceeded
from xsp.core.session import SessionContext, VastSession
from xsp.middleware.base import MiddlewareStack
from xsp.middleware.budget import Budget, BudgetTrackingMiddleware, InMemoryBudgetStore
from xsp.protocols.vast import VastUpstream, VastVersion
from xsp.transports.memory import MemoryTransport


# Sample VAST XML
SAMPLE_VAST = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="budget-demo-001">
        <InLine>
            <AdSystem>BudgetDemo</AdSystem>
            <AdTitle>Budget Tracking Example</AdTitle>
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


async def demo_global_budget_tracking():
    """
    Demonstrate global budget tracking.

    Track total advertising spend across all campaigns with a single
    global budget limit.
    """
    print("\n" + "=" * 70)
    print("DEMO 1: Global Budget Tracking")
    print("=" * 70)
    print("\nScenario: Track total ad spend with $500 global budget")
    print("-" * 70)

    # Create VAST upstream
    transport = MemoryTransport(SAMPLE_VAST.encode("utf-8"))
    vast_upstream = VastUpstream(
        transport=transport, endpoint="memory://global", version=VastVersion.V4_2
    )

    # Initialize budget store with global budget
    budget_store = InMemoryBudgetStore()
    global_budget = Budget(
        total_budget=Decimal("500.00"),
        spent=Decimal("0.00"),
        currency="USD",
        campaign_id=None,  # Global budget
    )
    budget_store._store["budget:global"] = global_budget

    # Create middleware
    budget_middleware = BudgetTrackingMiddleware(
        store=budget_store,
        default_cost=Decimal("50.00"),  # $50 per impression
        per_campaign=False,  # Global budget
    )

    middleware_stack = MiddlewareStack(budget_middleware)
    wrapped_upstream = middleware_stack.wrap(vast_upstream)

    print(f"Configuration:")
    print(f"  - Total budget: ${global_budget.total_budget} {global_budget.currency}")
    print(f"  - Cost per impression: $50.00")
    print(f"  - Per campaign: False (global)\n")

    # Make requests until budget is exhausted
    print("Making ad requests:")
    print("-" * 70)

    for i in range(1, 15):
        try:
            ctx = SessionContext(
                request_id=f"req-global-{i}",
                user_id=f"user-{i}",
                ip_address="10.0.0.1",
                timestamp=datetime.now(),
            )
            session = VastSession(wrapped_upstream, ctx)

            print(f"Request {i:2d}: ", end="")
            vast_xml = await session.fetch(params={"w": "640", "h": "480"}, cost=Decimal("50.00"))

            # Get updated budget
            current = await budget_store.get_budget("budget:global")
            remaining = current.total_budget - current.spent

            print(f"✓ Success")
            print(f"            Spent: ${current.spent} / ${current.total_budget}")
            print(f"            Remaining: ${remaining}")

            await session.close()

        except BudgetExceeded as e:
            print(f"✗ Budget exceeded!")
            print(f"            {e}")
            break

    # Final summary
    print("\n" + "-" * 70)
    final = await budget_store.get_budget("budget:global")
    if final:
        utilization = (final.spent / final.total_budget) * Decimal("100")
        print(f"Final budget status:")
        print(f"  Total budget: ${final.total_budget} {final.currency}")
        print(f"  Total spent: ${final.spent} {final.currency}")
        print(f"  Remaining: ${final.total_budget - final.spent} {final.currency}")
        print(f"  Utilization: {utilization:.1f}%")

    await vast_upstream.close()


async def demo_per_campaign_budgets():
    """
    Demonstrate per-campaign budget tracking.

    Manage separate budgets for different advertising campaigns.
    """
    print("\n" + "=" * 70)
    print("DEMO 2: Per-Campaign Budget Tracking")
    print("=" * 70)
    print("\nScenario: Track budgets for 3 different campaigns")
    print("-" * 70)

    # Create VAST upstream
    transport = MemoryTransport(SAMPLE_VAST.encode("utf-8"))
    vast_upstream = VastUpstream(
        transport=transport, endpoint="memory://campaigns", version=VastVersion.V4_2
    )

    # Initialize budget store with multiple campaign budgets
    budget_store = InMemoryBudgetStore()

    # Campaign A: High-budget brand campaign
    campaign_a = Budget(
        total_budget=Decimal("5000.00"),
        spent=Decimal("0.00"),
        currency="USD",
        campaign_id="campaign-brand-2024",
    )
    budget_store._store["budget:campaign:campaign-brand-2024"] = campaign_a

    # Campaign B: Mid-budget performance campaign
    campaign_b = Budget(
        total_budget=Decimal("2000.00"),
        spent=Decimal("0.00"),
        currency="USD",
        campaign_id="campaign-performance-2024",
    )
    budget_store._store["budget:campaign:campaign-performance-2024"] = campaign_b

    # Campaign C: Small test campaign
    campaign_c = Budget(
        total_budget=Decimal("500.00"),
        spent=Decimal("0.00"),
        currency="USD",
        campaign_id="campaign-test-2024",
    )
    budget_store._store["budget:campaign:campaign-test-2024"] = campaign_c

    # Create per-campaign middleware
    budget_middleware = BudgetTrackingMiddleware(
        store=budget_store,
        default_cost=Decimal("100.00"),
        per_campaign=True,  # Enable per-campaign tracking
    )

    middleware_stack = MiddlewareStack(budget_middleware)
    wrapped_upstream = middleware_stack.wrap(vast_upstream)

    print(f"Campaign budgets:")
    print(f"  - Brand Campaign: ${campaign_a.total_budget} USD")
    print(f"  - Performance Campaign: ${campaign_b.total_budget} USD")
    print(f"  - Test Campaign: ${campaign_c.total_budget} USD\n")

    # Simulate requests across campaigns
    campaigns = [
        ("campaign-brand-2024", Decimal("250.00"), 3),  # 3 requests at $250 each
        ("campaign-performance-2024", Decimal("150.00"), 5),  # 5 requests at $150 each
        ("campaign-test-2024", Decimal("100.00"), 6),  # 6 requests at $100 each (will exceed)
    ]

    for campaign_id, cost, num_requests in campaigns:
        print(f"Campaign: {campaign_id}")
        print("-" * 70)

        for i in range(1, num_requests + 1):
            try:
                ctx = SessionContext(
                    request_id=f"req-{campaign_id}-{i}",
                    user_id=f"user-{i}",
                    ip_address="10.0.0.1",
                    timestamp=datetime.now(),
                )
                session = VastSession(wrapped_upstream, ctx)

                print(f"  Request {i}: ", end="")
                vast_xml = await session.fetch(
                    params={"w": "1920", "h": "1080"}, campaign_id=campaign_id, cost=cost
                )

                # Get updated budget
                budget_key = f"budget:campaign:{campaign_id}"
                current = await budget_store.get_budget(budget_key)
                remaining = current.total_budget - current.spent

                print(f"✓ Cost ${cost}")
                print(f"              Spent: ${current.spent} / ${current.total_budget}")
                print(f"              Remaining: ${remaining}")

                await session.close()

            except BudgetExceeded as e:
                print(f"✗ Budget exceeded!")
                print(f"              Error: Campaign budget exhausted")
                break

        print()

    # Final summary
    print("-" * 70)
    print("Final campaign budgets:")
    for campaign_id in [
        "campaign-brand-2024",
        "campaign-performance-2024",
        "campaign-test-2024",
    ]:
        budget_key = f"budget:campaign:{campaign_id}"
        final = await budget_store.get_budget(budget_key)
        if final:
            remaining = final.total_budget - final.spent
            utilization = (final.spent / final.total_budget) * Decimal("100")
            print(f"\n  {campaign_id}:")
            print(f"    Total: ${final.total_budget} {final.currency}")
            print(f"    Spent: ${final.spent} {final.currency}")
            print(f"    Remaining: ${remaining} {final.currency}")
            print(f"    Utilization: {utilization:.1f}%")

    await vast_upstream.close()


async def demo_cost_calculation_methods():
    """
    Demonstrate different cost calculation methods.

    Shows how costs can be derived from:
    - Direct cost parameter
    - CPM (Cost Per Mille/Thousand impressions)
    - CPC (Cost Per Click) - simulated
    - Bid price from RTB context
    """
    print("\n" + "=" * 70)
    print("DEMO 3: Cost Calculation Methods")
    print("=" * 70)
    print("\nScenario: Different ways to calculate impression costs")
    print("-" * 70)

    # Create VAST upstream
    transport = MemoryTransport(SAMPLE_VAST.encode("utf-8"))
    vast_upstream = VastUpstream(
        transport=transport, endpoint="memory://costs", version=VastVersion.V4_2
    )

    # Initialize budget store
    budget_store = InMemoryBudgetStore()
    budget = Budget(
        total_budget=Decimal("1000.00"),
        spent=Decimal("0.00"),
        currency="USD",
        campaign_id="campaign-costs-demo",
    )
    budget_store._store["budget:campaign:campaign-costs-demo"] = budget

    budget_middleware = BudgetTrackingMiddleware(
        store=budget_store, default_cost=Decimal("1.00"), per_campaign=True
    )

    middleware_stack = MiddlewareStack(budget_middleware)
    wrapped_upstream = middleware_stack.wrap(vast_upstream)

    print("Testing different cost calculation methods:\n")

    # Method 1: Direct cost
    print("1. Direct cost parameter:")
    print("-" * 70)
    ctx = SessionContext(
        request_id="req-direct-cost",
        user_id="user-1",
        ip_address="10.0.0.1",
        timestamp=datetime.now(),
    )
    session = VastSession(wrapped_upstream, ctx)
    await session.fetch(
        params={"w": "640", "h": "480"},
        campaign_id="campaign-costs-demo",
        cost=Decimal("25.00"),  # Direct cost
    )
    current = await budget_store.get_budget("budget:campaign:campaign-costs-demo")
    print(f"  Cost: $25.00 (direct)")
    print(f"  Spent: ${current.spent}")
    await session.close()

    # Method 2: CPM (Cost Per Mille)
    print("\n2. CPM (Cost Per Mille) - $10 CPM:")
    print("-" * 70)
    ctx = SessionContext(
        request_id="req-cpm",
        user_id="user-2",
        ip_address="10.0.0.2",
        timestamp=datetime.now(),
    )
    session = VastSession(wrapped_upstream, ctx)
    await session.fetch(
        params={"w": "640", "h": "480"},
        campaign_id="campaign-costs-demo",
        cpm=Decimal("10.00"),  # $10 CPM = $0.01 per impression
    )
    current = await budget_store.get_budget("budget:campaign:campaign-costs-demo")
    cpm_cost = Decimal("10.00") / Decimal("1000")
    print(f"  CPM: $10.00")
    print(f"  Cost per impression: ${cpm_cost} ($10 / 1000)")
    print(f"  Total spent: ${current.spent}")
    await session.close()

    # Method 3: Bid price (from RTB context)
    print("\n3. Bid price (from RTB bid response):")
    print("-" * 70)
    ctx = SessionContext(
        request_id="req-bid",
        user_id="user-3",
        ip_address="10.0.0.3",
        timestamp=datetime.now(),
    )
    session = VastSession(wrapped_upstream, ctx)
    await session.fetch(
        params={"w": "640", "h": "480"},
        campaign_id="campaign-costs-demo",
        bid_price=Decimal("3.75"),  # Winning bid price
    )
    current = await budget_store.get_budget("budget:campaign:campaign-costs-demo")
    print(f"  Bid price: $3.75")
    print(f"  Total spent: ${current.spent}")
    await session.close()

    # Method 4: Default cost (no cost specified)
    print("\n4. Default cost (fallback):")
    print("-" * 70)
    ctx = SessionContext(
        request_id="req-default",
        user_id="user-4",
        ip_address="10.0.0.4",
        timestamp=datetime.now(),
    )
    session = VastSession(wrapped_upstream, ctx)
    await session.fetch(
        params={"w": "640", "h": "480"},
        campaign_id="campaign-costs-demo",
        # No cost parameter - uses default
    )
    current = await budget_store.get_budget("budget:campaign:campaign-costs-demo")
    print(f"  Default cost: $1.00")
    print(f"  Total spent: ${current.spent}")
    await session.close()

    # Summary
    print("\n" + "-" * 70)
    final = await budget_store.get_budget("budget:campaign:campaign-costs-demo")
    if final:
        print(f"Total spent across all methods: ${final.spent} {final.currency}")
        print(f"Remaining budget: ${final.total_budget - final.spent} {final.currency}")

    await vast_upstream.close()


async def demo_budget_reset():
    """
    Demonstrate budget reset functionality.

    Useful for monthly/quarterly budget resets or testing.
    """
    print("\n" + "=" * 70)
    print("DEMO 4: Budget Reset")
    print("=" * 70)
    print("\nScenario: Reset campaign budget for new period")
    print("-" * 70)

    # Initialize budget store
    budget_store = InMemoryBudgetStore()
    budget = Budget(
        total_budget=Decimal("1000.00"),
        spent=Decimal("750.00"),  # Already spent $750
        currency="USD",
        campaign_id="campaign-monthly",
    )
    budget_store._store["budget:campaign:campaign-monthly"] = budget

    print("Current budget state:")
    print(f"  Total: ${budget.total_budget} {budget.currency}")
    print(f"  Spent: ${budget.spent} {budget.currency}")
    print(f"  Remaining: ${budget.total_budget - budget.spent} {budget.currency}")

    # Reset budget
    print("\nResetting budget for new month...")
    await budget_store.reset("budget:campaign:campaign-monthly")

    # Check after reset
    reset_budget = await budget_store.get_budget("budget:campaign:campaign-monthly")
    if reset_budget:
        print(f"\nAfter reset:")
        print(f"  Total: ${reset_budget.total_budget} {reset_budget.currency}")
        print(f"  Spent: ${reset_budget.spent} {reset_budget.currency}")
        print(f"  Remaining: ${reset_budget.total_budget - reset_budget.spent} {reset_budget.currency}")
        print(f"  ✓ Budget reset successfully")


async def demo_decimal_precision():
    """
    Demonstrate importance of Decimal precision for financial calculations.

    Shows why Decimal should be used instead of float for money.
    """
    print("\n" + "=" * 70)
    print("DEMO 5: Decimal Precision (Why it Matters)")
    print("=" * 70)
    print("\nScenario: Financial precision in ad spend calculations")
    print("-" * 70)

    print("\n⚠️  Float precision issues:")
    float_sum = 0.0
    for _ in range(100):
        float_sum += 0.01  # Adding $0.01 one hundred times
    print(f"  100 × $0.01 with float: ${float_sum:.20f}")
    print(f"  Expected: $1.00")
    print(f"  Error: ${abs(1.0 - float_sum):.20f}")

    print("\n✓ Decimal precision (correct):")
    decimal_sum = Decimal("0.00")
    for _ in range(100):
        decimal_sum += Decimal("0.01")
    print(f"  100 × $0.01 with Decimal: ${decimal_sum}")
    print(f"  Expected: $1.00")
    print(f"  Error: ${abs(Decimal('1.00') - decimal_sum)}")

    print("\n" + "-" * 70)
    print("Best Practices:")
    print("  ✓ Always use Decimal for monetary values")
    print("  ✓ Initialize with strings: Decimal('10.50')")
    print("  ✓ Never use float for financial calculations")
    print("  ✓ Use 2+ decimal places for sub-currency precision")


async def main() -> None:
    """Run all budget tracking demonstrations."""
    print("\n" + "=" * 70)
    print("XSP-Lib Budget Tracking Middleware Examples")
    print("=" * 70)

    # Run all demos
    await demo_global_budget_tracking()
    await demo_per_campaign_budgets()
    await demo_cost_calculation_methods()
    await demo_budget_reset()
    await demo_decimal_precision()

    print("\n" + "=" * 70)
    print("All demonstrations complete!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. Always use Decimal for financial precision")
    print("  2. Budget tracking prevents campaign overspend")
    print("  3. Per-campaign budgets enable flexible management")
    print("  4. Multiple cost calculation methods supported")
    print("  5. Budget reset for periodic renewals")
    print("\nFor production use:")
    print("  - Replace InMemoryBudgetStore with Redis/database")
    print("  - Implement rollback on failed requests")
    print("  - Add budget pacing for even spend distribution")
    print("  - Monitor utilization and adjust campaigns\n")


if __name__ == "__main__":
    asyncio.run(main())
