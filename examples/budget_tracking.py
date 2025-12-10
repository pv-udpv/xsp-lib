"""Budget Tracking Example.

This example demonstrates campaign budget tracking with xsp-lib:
- Setting and monitoring campaign budgets
- Recording ad spend (CPM, CPC, CPA)
- Enforcing budget limits
- Budget exhaustion handling
- Multi-campaign budget management

Budget tracking ensures campaigns stay within spend limits, preventing
over-delivery and protecting advertiser ROI.
"""

import asyncio
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import uuid4

from xsp.core.base import BaseUpstream
from xsp.core.exceptions import XspError
from xsp.transports.memory import MemoryTransport


# ============================================================================
# Exceptions
# ============================================================================


class BudgetExceeded(XspError):
    """Raised when campaign budget is exceeded."""

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

    def clear(self) -> None:
        """Clear all data."""
        self._data.clear()


# ============================================================================
# Budget Tracker
# ============================================================================


class BudgetTracker:
    """Track campaign budget and spend.

    Supports:
    - Budget initialization
    - Spend recording (CPM, CPC, CPA)
    - Remaining budget queries
    - Budget exhaustion detection
    """

    def __init__(self, backend: MemoryBackend):
        """Initialize budget tracker.

        Args:
            backend: State backend for persistence
        """
        self.backend = backend

    async def set_budget(
        self,
        campaign_id: str,
        budget: Decimal,
        currency: str = "USD",
    ) -> None:
        """Set campaign budget.

        Args:
            campaign_id: Campaign identifier
            budget: Total budget in currency units
            currency: Currency code (default: USD)
        """
        key = self._make_key(campaign_id)
        await self.backend.set(
            key,
            {
                "total": float(budget),
                "spent": 0.0,
                "remaining": float(budget),
                "currency": currency,
                "impressions": 0,
                "clicks": 0,
                "conversions": 0,
            },
        )

    async def record_spend(
        self,
        campaign_id: str,
        amount: Decimal,
        impressions: int = 0,
        clicks: int = 0,
        conversions: int = 0,
    ) -> dict[str, Any]:
        """Record spend and return updated budget.

        Args:
            campaign_id: Campaign identifier
            amount: Spend amount
            impressions: Number of impressions (optional)
            clicks: Number of clicks (optional)
            conversions: Number of conversions (optional)

        Returns:
            Updated budget dict with total, spent, remaining

        Raises:
            BudgetExceeded: If spend would exceed budget
        """
        key = self._make_key(campaign_id)
        budget = await self.backend.get(key)

        if budget is None:
            raise ValueError(f"No budget set for campaign {campaign_id}")

        new_spent = budget["spent"] + float(amount)
        new_remaining = budget["total"] - new_spent

        if new_remaining < 0:
            raise BudgetExceeded(
                f"Campaign {campaign_id} budget exceeded: "
                f"attempted spend ${amount:.2f}, "
                f"remaining ${budget['remaining']:.2f}, "
                f"total budget ${budget['total']:.2f}"
            )

        updated = {
            "total": budget["total"],
            "spent": new_spent,
            "remaining": new_remaining,
            "currency": budget["currency"],
            "impressions": budget["impressions"] + impressions,
            "clicks": budget["clicks"] + clicks,
            "conversions": budget["conversions"] + conversions,
        }

        await self.backend.set(key, updated)
        return updated

    async def get_budget(self, campaign_id: str) -> dict[str, Any] | None:
        """Get campaign budget details.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Budget dict or None if not set
        """
        key = self._make_key(campaign_id)
        return await self.backend.get(key)

    async def get_remaining(self, campaign_id: str) -> Decimal:
        """Get remaining budget.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Remaining budget amount
        """
        budget = await self.get_budget(campaign_id)

        if budget is None:
            return Decimal("0")

        return Decimal(str(budget["remaining"]))

    async def check_available(
        self,
        campaign_id: str,
        required_amount: Decimal,
    ) -> bool:
        """Check if budget is available for spend.

        Args:
            campaign_id: Campaign identifier
            required_amount: Amount needed

        Returns:
            True if budget available, False otherwise
        """
        remaining = await self.get_remaining(campaign_id)
        return remaining >= required_amount

    def _make_key(self, campaign_id: str) -> str:
        """Generate cache key for budget."""
        return f"budget:{campaign_id}"


# ============================================================================
# Budget-Aware Session Upstream
# ============================================================================


class BudgetTrackedSessionUpstream(BaseUpstream[str]):
    """Session upstream with budget tracking."""

    def __init__(
        self,
        *args: Any,
        budget_tracker: BudgetTracker,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.budget_tracker = budget_tracker
        self._context: SessionContext | None = None
        self._session_state: dict[str, Any] = {}

    async def start_session(self, context: SessionContext) -> None:
        """Initialize session."""
        if self._context is not None:
            raise XspError("Session already started")

        self._context = context
        self._session_state = {"request_count": 0, "total_spend": Decimal("0")}

    async def fetch_with_session(
        self,
        campaign_id: str,
        cost: Decimal,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Fetch ad with budget check.

        Args:
            campaign_id: Campaign identifier
            cost: Cost of this impression
            params: Request parameters
            **kwargs: Additional arguments

        Returns:
            Ad response

        Raises:
            XspError: If session not started
            BudgetExceeded: If budget insufficient
        """
        if self._context is None:
            raise XspError("Session not started")

        # Check budget availability
        available = await self.budget_tracker.check_available(campaign_id, cost)

        if not available:
            budget = await self.budget_tracker.get_budget(campaign_id)
            raise BudgetExceeded(
                f"Insufficient budget for campaign {campaign_id}: "
                f"need ${cost:.2f}, "
                f"remaining ${budget['remaining']:.2f}" if budget else "budget not set"
            )

        # Fetch ad
        result = await self.fetch(params=params, **kwargs)

        # Record spend
        await self.budget_tracker.record_spend(
            campaign_id=campaign_id,
            amount=cost,
            impressions=1,
        )

        # Update session state
        self._session_state["request_count"] = (
            self._session_state.get("request_count", 0) + 1
        )
        current_spend = self._session_state.get("total_spend", Decimal("0"))
        self._session_state["total_spend"] = current_spend + cost

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
# Example 1: Basic Budget Tracking
# ============================================================================


async def example_basic_budget_tracking() -> None:
    """Demonstrate basic budget tracking."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Budget Tracking")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    tracker = BudgetTracker(backend)

    # Set campaign budget
    campaign_id = "camp_basic"
    budget = Decimal("100.00")

    await tracker.set_budget(campaign_id, budget)

    print(f"Campaign: {campaign_id}")
    print(f"Total budget: ${budget}\n")

    # Simulate ad impressions with CPM pricing
    cpm = Decimal("5.00")  # $5 CPM
    cost_per_impression = cpm / Decimal("1000")

    print(f"Pricing model: ${cpm} CPM")
    print(f"Cost per impression: ${cost_per_impression:.4f}\n")

    impressions_served = 0

    for i in range(5):
        try:
            budget_info = await tracker.record_spend(
                campaign_id=campaign_id,
                amount=cost_per_impression,
                impressions=1,
            )

            impressions_served += 1

            print(
                f"Impression {i + 1}: "
                f"spent=${budget_info['spent']:.4f}, "
                f"remaining=${budget_info['remaining']:.4f}"
            )

        except BudgetExceeded as e:
            print(f"Impression {i + 1}: ✗ Budget exceeded")
            break

    budget_final = await tracker.get_budget(campaign_id)
    print(f"\nFinal stats:")
    print(f"  Impressions: {budget_final['impressions']}")
    print(f"  Total spent: ${budget_final['spent']:.2f}")
    print(f"  Remaining: ${budget_final['remaining']:.2f}")
    print(f"  Effective CPM: ${(budget_final['spent'] / budget_final['impressions']) * 1000:.2f}")

    print("\n")


# ============================================================================
# Example 2: Budget Exhaustion
# ============================================================================


async def example_budget_exhaustion() -> None:
    """Demonstrate budget exhaustion handling."""
    print("\n" + "=" * 70)
    print("Example 2: Budget Exhaustion")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    tracker = BudgetTracker(backend)

    campaign_id = "camp_exhaust"
    budget = Decimal("10.00")  # Small budget for quick exhaustion

    await tracker.set_budget(campaign_id, budget)

    mock_ad = b"<VAST><Ad><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"

    upstream = BudgetTrackedSessionUpstream(
        transport=MemoryTransport(mock_ad),
        decoder=lambda b: b.decode("utf-8"),
        endpoint="memory://vast",
        budget_tracker=tracker,
    )

    context = SessionContext(session_id=str(uuid4()), user_id="user_12345")
    await upstream.start_session(context)

    print(f"Campaign: {campaign_id}")
    print(f"Budget: ${budget}")
    print(f"Cost per impression: $2.00\n")

    impression_cost = Decimal("2.00")
    served = 0
    blocked = 0

    try:
        # Try to serve 10 impressions (budget allows only 5)
        for i in range(10):
            try:
                await upstream.fetch_with_session(
                    campaign_id=campaign_id,
                    cost=impression_cost,
                )
                served += 1
                remaining = await tracker.get_remaining(campaign_id)
                print(f"Impression {i + 1}: ✓ Served (remaining: ${remaining:.2f})")

            except BudgetExceeded as e:
                blocked += 1
                print(f"Impression {i + 1}: ✗ Blocked (budget exhausted)")

    finally:
        await upstream.end_session()

    print(f"\nSummary:")
    print(f"  Impressions served: {served}")
    print(f"  Impressions blocked: {blocked}")
    print(f"  Budget utilization: {(served * float(impression_cost)) / float(budget) * 100:.1f}%")

    print("\n")


# ============================================================================
# Example 3: Multi-Campaign Budget Management
# ============================================================================


async def example_multi_campaign_budgets() -> None:
    """Demonstrate managing budgets across multiple campaigns."""
    print("\n" + "=" * 70)
    print("Example 3: Multi-Campaign Budget Management")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    tracker = BudgetTracker(backend)

    # Set up multiple campaigns with different budgets
    campaigns = {
        "camp_premium": Decimal("500.00"),
        "camp_standard": Decimal("250.00"),
        "camp_economy": Decimal("100.00"),
    }

    print("Campaign budgets:")
    for campaign_id, budget in campaigns.items():
        await tracker.set_budget(campaign_id, budget)
        print(f"  {campaign_id}: ${budget}")

    print("\nServing ads from all campaigns...\n")

    mock_ad = b"<VAST><Ad><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"

    # Different pricing for each campaign tier
    pricing = {
        "camp_premium": Decimal("10.00"),  # $10 per impression
        "camp_standard": Decimal("5.00"),  # $5 per impression
        "camp_economy": Decimal("2.00"),  # $2 per impression
    }

    # Serve impressions from each campaign
    for campaign_id in campaigns.keys():
        upstream = BudgetTrackedSessionUpstream(
            transport=MemoryTransport(mock_ad),
            decoder=lambda b: b.decode("utf-8"),
            endpoint="memory://vast",
            budget_tracker=tracker,
        )

        context = SessionContext(session_id=str(uuid4()), user_id=f"user_{campaign_id}")
        await upstream.start_session(context)

        print(f"Campaign: {campaign_id} (${pricing[campaign_id]}/impression)")

        try:
            # Serve 3 impressions from each
            for i in range(3):
                await upstream.fetch_with_session(
                    campaign_id=campaign_id,
                    cost=pricing[campaign_id],
                )
                budget_info = await tracker.get_budget(campaign_id)
                print(
                    f"  Impression {i + 1}: "
                    f"spent=${budget_info['spent']:.2f}, "
                    f"remaining=${budget_info['remaining']:.2f}"
                )

        finally:
            await upstream.end_session()

        print()

    # Summary across all campaigns
    print("=" * 70)
    print("Budget Summary Across All Campaigns")
    print("=" * 70)

    total_budget = Decimal("0")
    total_spent = Decimal("0")

    for campaign_id in campaigns.keys():
        budget_info = await tracker.get_budget(campaign_id)
        total_budget += Decimal(str(budget_info["total"]))
        total_spent += Decimal(str(budget_info["spent"]))

        print(f"\n{campaign_id}:")
        print(f"  Budget: ${budget_info['total']:.2f}")
        print(f"  Spent: ${budget_info['spent']:.2f}")
        print(f"  Remaining: ${budget_info['remaining']:.2f}")
        print(f"  Impressions: {budget_info['impressions']}")

    print(f"\nOverall:")
    print(f"  Total budget: ${total_budget:.2f}")
    print(f"  Total spent: ${total_spent:.2f}")
    print(f"  Overall utilization: {(total_spent / total_budget * 100):.1f}%")

    print("\n")


# ============================================================================
# Example 4: CPM, CPC, and CPA Tracking
# ============================================================================


async def example_pricing_models() -> None:
    """Demonstrate different pricing models (CPM, CPC, CPA)."""
    print("\n" + "=" * 70)
    print("Example 4: Multiple Pricing Models (CPM, CPC, CPA)")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    tracker = BudgetTracker(backend)

    # Campaign with mixed pricing
    campaign_id = "camp_mixed"
    budget = Decimal("1000.00")

    await tracker.set_budget(campaign_id, budget)

    print(f"Campaign: {campaign_id}")
    print(f"Budget: ${budget}")
    print("\nPricing models:")
    print("  CPM: $5.00 per 1000 impressions")
    print("  CPC: $0.50 per click")
    print("  CPA: $10.00 per conversion\n")

    # Simulate ad serving with various actions
    scenarios = [
        {"impressions": 1000, "clicks": 0, "conversions": 0, "label": "1000 impressions (CPM)"},
        {"impressions": 1, "clicks": 10, "conversions": 0, "label": "10 clicks (CPC)"},
        {"impressions": 1, "clicks": 1, "conversions": 1, "label": "1 conversion (CPA)"},
    ]

    cpm = Decimal("5.00")
    cpc = Decimal("0.50")
    cpa = Decimal("10.00")

    for scenario in scenarios:
        # Calculate cost
        cost = (
            (Decimal(str(scenario["impressions"])) / Decimal("1000") * cpm)
            + (Decimal(str(scenario["clicks"])) * cpc)
            + (Decimal(str(scenario["conversions"])) * cpa)
        )

        # Record spend
        budget_info = await tracker.record_spend(
            campaign_id=campaign_id,
            amount=cost,
            impressions=scenario["impressions"],
            clicks=scenario["clicks"],
            conversions=scenario["conversions"],
        )

        print(f"{scenario['label']}:")
        print(f"  Cost: ${cost:.2f}")
        print(f"  Spent: ${budget_info['spent']:.2f}")
        print(f"  Remaining: ${budget_info['remaining']:.2f}\n")

    # Final stats
    budget_final = await tracker.get_budget(campaign_id)
    print("Final campaign statistics:")
    print(f"  Total impressions: {budget_final['impressions']:,}")
    print(f"  Total clicks: {budget_final['clicks']}")
    print(f"  Total conversions: {budget_final['conversions']}")
    print(f"  Total spent: ${budget_final['spent']:.2f}")
    print(f"  Remaining budget: ${budget_final['remaining']:.2f}")

    if budget_final["impressions"] > 0:
        print(f"  Effective CPM: ${(budget_final['spent'] / budget_final['impressions']) * 1000:.2f}")
    if budget_final["clicks"] > 0:
        print(f"  Effective CPC: ${budget_final['spent'] / budget_final['clicks']:.2f}")
    if budget_final["conversions"] > 0:
        print(f"  Effective CPA: ${budget_final['spent'] / budget_final['conversions']:.2f}")

    print("\n")


# ============================================================================
# Example 5: Production Budget Tracking
# ============================================================================


async def example_production_budget_tracking() -> None:
    """Demonstrate production-ready budget tracking with error recovery."""
    print("\n" + "=" * 70)
    print("Example 5: Production Budget Tracking with Error Handling")
    print("=" * 70 + "\n")

    backend = MemoryBackend()
    tracker = BudgetTracker(backend)

    # Set up multiple campaigns
    campaigns = {
        "camp_active": Decimal("1000.00"),
        "camp_depleted": Decimal("5.00"),  # Will deplete quickly
    }

    for campaign_id, budget in campaigns.items():
        await tracker.set_budget(campaign_id, budget)

    print("Production ad serving simulation\n")

    mock_ad = b"<VAST><Ad><InLine><AdTitle>Ad</AdTitle></InLine></Ad></VAST>"

    metrics = {
        "requests": 0,
        "served": 0,
        "budget_blocks": 0,
        "errors": 0,
    }

    # Simulate production traffic
    for i in range(20):
        metrics["requests"] += 1

        # Alternate between campaigns
        campaign_id = "camp_active" if i % 2 == 0 else "camp_depleted"
        cost = Decimal("2.50")

        upstream = BudgetTrackedSessionUpstream(
            transport=MemoryTransport(mock_ad),
            decoder=lambda b: b.decode("utf-8"),
            endpoint="memory://vast",
            budget_tracker=tracker,
        )

        context = SessionContext(session_id=str(uuid4()), user_id=f"user_{i}")

        try:
            await upstream.start_session(context)

            try:
                # Check budget before serving
                available = await tracker.check_available(campaign_id, cost)

                if not available:
                    metrics["budget_blocks"] += 1
                    print(f"Request {i + 1}: {campaign_id} - ✗ Budget depleted, serve fallback ad")
                    continue

                # Serve ad
                await upstream.fetch_with_session(
                    campaign_id=campaign_id,
                    cost=cost,
                )

                metrics["served"] += 1
                budget_info = await tracker.get_budget(campaign_id)
                print(
                    f"Request {i + 1}: {campaign_id} - ✓ Served "
                    f"(remaining: ${budget_info['remaining']:.2f})"
                )

            except BudgetExceeded:
                metrics["budget_blocks"] += 1
                print(f"Request {i + 1}: {campaign_id} - ✗ Budget check failed")

            except Exception as e:
                metrics["errors"] += 1
                print(f"Request {i + 1}: {campaign_id} - ✗ Error: {e}")

        finally:
            # Always clean up, even on error
            try:
                await upstream.end_session()
            except Exception:
                pass  # Log but don't raise during cleanup

    # Production metrics
    print("\n" + "=" * 70)
    print("Production Metrics")
    print("=" * 70)
    print(f"Total requests: {metrics['requests']}")
    print(f"Ads served: {metrics['served']}")
    print(f"Blocked by budget: {metrics['budget_blocks']}")
    print(f"Errors: {metrics['errors']}")
    print(f"Success rate: {(metrics['served'] / metrics['requests']) * 100:.1f}%")

    print("\nCampaign budgets:")
    for campaign_id in campaigns.keys():
        budget_info = await tracker.get_budget(campaign_id)
        print(f"\n{campaign_id}:")
        print(f"  Budget: ${budget_info['total']:.2f}")
        print(f"  Spent: ${budget_info['spent']:.2f}")
        print(f"  Remaining: ${budget_info['remaining']:.2f}")
        print(f"  Utilization: {(budget_info['spent'] / budget_info['total']) * 100:.1f}%")

    print("\n")


# ============================================================================
# Main
# ============================================================================


async def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 70)
    print("XSP-LIB BUDGET TRACKING EXAMPLES")
    print("=" * 70)

    await example_basic_budget_tracking()
    await example_budget_exhaustion()
    await example_multi_campaign_budgets()
    await example_pricing_models()
    await example_production_budget_tracking()

    print("=" * 70)
    print("All examples completed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
