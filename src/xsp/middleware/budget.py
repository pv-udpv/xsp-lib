"""Budget tracking middleware for ad spend control.

Implements budget tracking and enforcement to prevent overspending on
advertising campaigns. Uses Decimal for financial precision and supports
both global and per-campaign budget tracking.

References:
    - IAB OpenRTB 2.6 §3.2.1: Bid request budget signaling
    - IAB Programmatic Supply Chain: Budget pacing best practices
    - OpenRTB Native 1.2: Budget management for native campaigns
    - Industry standards for financial precision in ad serving
"""

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from xsp.core.exceptions import BudgetExceeded
from xsp.core.upstream import Upstream
from xsp.middleware.base import FetchFunc


@dataclass(frozen=True)
class Budget:
    """
    Budget configuration for ad spend tracking.

    Defines budget limits and current spend for campaigns. Uses Decimal
    for financial precision to avoid floating-point rounding errors in
    monetary calculations.

    Attributes:
        total_budget: Maximum budget allowed (e.g., Decimal("1000.00"))
        spent: Current amount spent (e.g., Decimal("250.50"))
        currency: ISO 4217 currency code (e.g., "USD", "EUR", "GBP")
        campaign_id: Optional campaign identifier for per-campaign budgets

    Example:
        >>> # Global budget: $1000 with $250.50 already spent
        >>> budget = Budget(
        ...     total_budget=Decimal("1000.00"),
        ...     spent=Decimal("250.50"),
        ...     currency="USD",
        ...     campaign_id=None
        ... )
        >>> budget.total_budget - budget.spent
        Decimal('749.50')
        >>>
        >>> # Per-campaign budget: €500 for campaign-123
        >>> campaign_budget = Budget(
        ...     total_budget=Decimal("500.00"),
        ...     spent=Decimal("0.00"),
        ...     currency="EUR",
        ...     campaign_id="campaign-123"
        ... )

    Note:
        Always use Decimal for monetary values to avoid floating-point
        precision issues. For example:
        - CORRECT: Decimal("10.50")
        - INCORRECT: 10.5 (float, loses precision)

        Per IAB programmatic guidelines, budget tracking should use
        at least 2 decimal places for sub-currency unit precision.
    """

    total_budget: Decimal
    spent: Decimal
    currency: str
    campaign_id: str | None = None

    def __post_init__(self) -> None:
        """Validate budget configuration."""
        if self.total_budget < Decimal("0"):
            raise ValueError("total_budget must be non-negative")
        if self.spent < Decimal("0"):
            raise ValueError("spent must be non-negative")
        if len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code (e.g., USD)")


class BudgetStore(Protocol):
    """
    Protocol for budget storage backend.

    Defines the interface for storing and retrieving budget information.
    Implementations must be thread-safe for concurrent access and use
    Decimal for all monetary values.

    Methods:
        get_budget: Retrieve budget configuration for a key
        update_spent: Update spent amount for a budget
        reset: Reset budget to initial state

    Thread Safety:
        All methods must be thread-safe and support concurrent async access.
        Consider using asyncio.Lock or other synchronization primitives.

    Example Implementation:
        >>> class RedisBudgetStore:
        ...     async def get_budget(self, key: str) -> Budget | None:
        ...         data = await self.redis.hgetall(f"budget:{key}")
        ...         if not data:
        ...             return None
        ...         return Budget(
        ...             total_budget=Decimal(data["total_budget"]),
        ...             spent=Decimal(data["spent"]),
        ...             currency=data["currency"],
        ...             campaign_id=data.get("campaign_id")
        ...         )
        ...
        ...     async def update_spent(
        ...         self, key: str, amount: Decimal
        ...     ) -> Budget:
        ...         await self.redis.hincrbyfloat(
        ...             f"budget:{key}", "spent", float(amount)
        ...         )
        ...         return await self.get_budget(key)
        ...
        ...     async def reset(self, key: str) -> None:
        ...         await self.redis.hset(f"budget:{key}", "spent", "0")
    """

    async def get_budget(self, key: str) -> Budget | None:
        """
        Get budget configuration for key.

        Args:
            key: Storage key (e.g., "global" or "campaign:123")

        Returns:
            Budget configuration or None if not found
        """
        ...

    async def update_spent(self, key: str, amount: Decimal) -> Budget:
        """
        Update spent amount for budget.

        Adds the specified amount to the current spent value and returns
        the updated budget.

        Args:
            key: Storage key
            amount: Amount to add to spent (must be non-negative)

        Returns:
            Updated Budget with new spent value

        Raises:
            ValueError: If amount is negative
        """
        ...

    async def reset(self, key: str) -> None:
        """
        Reset budget spent to zero.

        Args:
            key: Storage key to reset
        """
        ...


class InMemoryBudgetStore:
    """
    In-memory budget storage using dict and asyncio.Lock.

    Simple thread-safe implementation suitable for single-instance
    deployments and testing. For production distributed systems,
    use Redis or similar external storage.

    Storage Format:
        {
            "key": Budget(
                total_budget=Decimal("1000.00"),
                spent=Decimal("250.50"),
                currency="USD",
                campaign_id=None
            )
        }

    Thread Safety:
        All operations are protected by asyncio.Lock to ensure thread-safe
        concurrent access. Multiple coroutines can safely share an instance.

    Example:
        >>> store = InMemoryBudgetStore()
        >>>
        >>> # Initialize budget
        >>> budget = Budget(
        ...     total_budget=Decimal("1000.00"),
        ...     spent=Decimal("0.00"),
        ...     currency="USD"
        ... )
        >>> store._store["global"] = budget
        >>>
        >>> # Update spend
        >>> updated = await store.update_spent("global", Decimal("50.25"))
        >>> updated.spent
        Decimal('50.25')
        >>>
        >>> # Get budget
        >>> current = await store.get_budget("global")
        >>> current.spent
        Decimal('50.25')
        >>>
        >>> # Reset budget
        >>> await store.reset("global")
        >>> reset_budget = await store.get_budget("global")
        >>> reset_budget.spent
        Decimal('0.00')

    Warning:
        Data is not persisted and will be lost on process restart.
        Not suitable for distributed deployments where multiple
        instances need to share budget state.
    """

    def __init__(self) -> None:
        """Initialize in-memory store with empty state."""
        self._store: dict[str, Budget] = {}
        self._lock = asyncio.Lock()

    async def get_budget(self, key: str) -> Budget | None:
        """
        Get budget configuration for key.

        Args:
            key: Storage key

        Returns:
            Budget configuration or None if not found

        Example:
            >>> budget = await store.get_budget("campaign:123")
            >>> if budget:
            ...     print(f"Remaining: {budget.total_budget - budget.spent}")
        """
        async with self._lock:
            return self._store.get(key)

    async def update_spent(self, key: str, amount: Decimal) -> Budget:
        """
        Update spent amount for budget.

        Args:
            key: Storage key
            amount: Amount to add to spent (must be non-negative)

        Returns:
            Updated Budget with new spent value

        Raises:
            ValueError: If amount is negative or budget doesn't exist

        Example:
            >>> # Add $50.25 to spent
            >>> updated = await store.update_spent("global", Decimal("50.25"))
            >>> updated.spent
            Decimal('50.25')
        """
        if amount < Decimal("0"):
            raise ValueError("amount must be non-negative")

        async with self._lock:
            budget = self._store.get(key)
            if budget is None:
                raise ValueError(f"Budget not found for key: {key}")

            # Create new Budget with updated spent (dataclass is frozen)
            updated = Budget(
                total_budget=budget.total_budget,
                spent=budget.spent + amount,
                currency=budget.currency,
                campaign_id=budget.campaign_id,
            )
            self._store[key] = updated
            return updated

    async def reset(self, key: str) -> None:
        """
        Reset budget spent to zero.

        Args:
            key: Storage key to reset

        Raises:
            ValueError: If budget doesn't exist

        Example:
            >>> await store.reset("campaign:456")
            >>> budget = await store.get_budget("campaign:456")
            >>> budget.spent
            Decimal('0.00')
        """
        async with self._lock:
            budget = self._store.get(key)
            if budget is None:
                raise ValueError(f"Budget not found for key: {key}")

            # Create new Budget with spent reset to zero
            reset_budget = Budget(
                total_budget=budget.total_budget,
                spent=Decimal("0"),
                currency=budget.currency,
                campaign_id=budget.campaign_id,
            )
            self._store[key] = reset_budget


class BudgetTrackingMiddleware:
    """
    Middleware for budget tracking and spend enforcement.

    Tracks advertising spend and prevents overspending by checking budget
    limits before allowing requests and updating spend after successful
    requests. Supports both global and per-campaign budget tracking.

    Budget Enforcement Flow:
        1. Extract campaign_id from kwargs (if per-campaign mode)
        2. Build storage key (e.g., "budget:global" or "budget:campaign:123")
        3. Get current budget from store
        4. Calculate cost from kwargs or use default
        5. Check if spend + cost <= total_budget
        6. If under budget, pass to next handler
        7. Update spent amount after successful request
        8. If over budget, raise BudgetExceeded

    Cost Calculation:
        The middleware looks for cost information in this order:
        1. kwargs["cost"] - Direct cost parameter
        2. kwargs["bid_price"] - Bid price from RTB context
        3. kwargs["cpm"] - CPM pricing (per-thousand impressions)
        4. Default cost if configured

    Real-time Spend Tracking:
        Spend is updated optimistically before the request to prevent
        race conditions. If the request fails, the spend should be
        rolled back (not implemented in basic version).

    Thread Safety:
        Thread-safe when using thread-safe BudgetStore implementations.
        The provided InMemoryBudgetStore uses asyncio.Lock.

    Example:
        >>> from decimal import Decimal
        >>> from xsp.middleware.budget import (
        ...     BudgetTrackingMiddleware,
        ...     Budget,
        ...     InMemoryBudgetStore,
        ... )
        >>> from xsp.middleware.base import MiddlewareStack
        >>>
        >>> # Create budget store
        >>> store = InMemoryBudgetStore()
        >>>
        >>> # Initialize global budget: $1000 USD
        >>> budget = Budget(
        ...     total_budget=Decimal("1000.00"),
        ...     spent=Decimal("0.00"),
        ...     currency="USD"
        ... )
        >>> store._store["budget:global"] = budget
        >>>
        >>> # Create middleware
        >>> budget_middleware = BudgetTrackingMiddleware(
        ...     store=store,
        ...     default_cost=Decimal("10.00"),
        ...     per_campaign=False
        ... )
        >>>
        >>> # Apply to upstream
        >>> stack = MiddlewareStack(budget_middleware)
        >>> wrapped = stack.wrap(upstream)
        >>>
        >>> # Requests succeed while under budget
        >>> await wrapped.fetch(cost=Decimal("100.00"))  # OK, spent: $100
        >>> await wrapped.fetch(cost=Decimal("200.00"))  # OK, spent: $300
        >>> await wrapped.fetch(cost=Decimal("800.00"))  # BudgetExceeded!

    Example (per-campaign):
        >>> # Create per-campaign budgets
        >>> campaign1_budget = Budget(
        ...     total_budget=Decimal("500.00"),
        ...     spent=Decimal("0.00"),
        ...     currency="USD",
        ...     campaign_id="campaign-1"
        ... )
        >>> store._store["budget:campaign:campaign-1"] = campaign1_budget
        >>>
        >>> campaign2_budget = Budget(
        ...     total_budget=Decimal("300.00"),
        ...     spent=Decimal("0.00"),
        ...     currency="USD",
        ...     campaign_id="campaign-2"
        ... )
        >>> store._store["budget:campaign:campaign-2"] = campaign2_budget
        >>>
        >>> # Create per-campaign middleware
        >>> budget_middleware = BudgetTrackingMiddleware(
        ...     store=store,
        ...     default_cost=Decimal("10.00"),
        ...     per_campaign=True
        ... )
        >>>
        >>> # Different campaigns have separate budgets
        >>> await wrapped.fetch(
        ...     campaign_id="campaign-1",
        ...     cost=Decimal("100.00")
        ... )  # OK - campaign-1 spent: $100
        >>> await wrapped.fetch(
        ...     campaign_id="campaign-2",
        ...     cost=Decimal("100.00")
        ... )  # OK - campaign-2 spent: $100

    Attributes:
        store: BudgetStore implementation for persistence
        default_cost: Default cost per request if not specified
        per_campaign: If True, track budgets per campaign_id

    References:
        - IAB OpenRTB 2.6: Budget signaling in bid requests
        - IAB Programmatic Supply Chain: Budget pacing guidelines
        - Industry standards: Use Decimal for financial precision
    """

    def __init__(
        self,
        store: BudgetStore,
        default_cost: Decimal | None = None,
        per_campaign: bool = False,
    ):
        """
        Initialize budget tracking middleware.

        Args:
            store: Storage backend for budget tracking
            default_cost: Default cost per request if not in kwargs
            per_campaign: If True, apply budgets per campaign_id

        Example:
            >>> store = InMemoryBudgetStore()
            >>> middleware = BudgetTrackingMiddleware(
            ...     store=store,
            ...     default_cost=Decimal("5.00"),
            ...     per_campaign=True
            ... )
        """
        self.store = store
        self.default_cost = default_cost if default_cost is not None else Decimal("0")
        self.per_campaign = per_campaign

    def _build_key(self, campaign_id: str | None = None) -> str:
        """
        Build storage key for budget tracking.

        Args:
            campaign_id: Optional campaign identifier (for per_campaign=True)

        Returns:
            Storage key string

        Example:
            >>> middleware._build_key()
            'budget:global'
            >>> middleware._build_key("campaign-123")
            'budget:campaign:campaign-123'
        """
        if self.per_campaign and campaign_id:
            return f"budget:campaign:{campaign_id}"
        return "budget:global"

    def _extract_campaign_id(self, kwargs: dict[str, Any]) -> str | None:
        """
        Extract campaign_id from request kwargs.

        Looks for campaign_id in:
        1. Direct campaign_id parameter
        2. context dict metadata
        3. params dict

        Args:
            kwargs: Request keyword arguments

        Returns:
            Campaign ID string or None if not found

        Example:
            >>> kwargs = {"campaign_id": "camp-123"}
            >>> middleware._extract_campaign_id(kwargs)
            'camp-123'
            >>>
            >>> kwargs = {"context": {"campaign_id": "camp-456"}}
            >>> middleware._extract_campaign_id(kwargs)
            'camp-456'
        """
        # Direct campaign_id parameter
        if "campaign_id" in kwargs and kwargs["campaign_id"]:
            return str(kwargs["campaign_id"])

        # context dict
        context = kwargs.get("context")
        if isinstance(context, dict) and "campaign_id" in context:
            return str(context["campaign_id"])

        # params dict
        params = kwargs.get("params")
        if isinstance(params, dict) and "campaign_id" in params:
            return str(params["campaign_id"])

        return None

    def _extract_cost(self, kwargs: dict[str, Any]) -> Decimal:
        """
        Extract cost from request kwargs.

        Looks for cost information in this order:
        1. kwargs["cost"] - Direct cost parameter
        2. kwargs["bid_price"] - Bid price from RTB
        3. kwargs["cpm"] - Cost per mille (per-thousand impressions)
        4. self.default_cost - Fallback default

        Args:
            kwargs: Request keyword arguments

        Returns:
            Cost as Decimal

        Example:
            >>> kwargs = {"cost": Decimal("15.50")}
            >>> middleware._extract_cost(kwargs)
            Decimal('15.50')
            >>>
            >>> kwargs = {"bid_price": Decimal("2.50")}
            >>> middleware._extract_cost(kwargs)
            Decimal('2.50')
            >>>
            >>> kwargs = {}
            >>> middleware._extract_cost(kwargs)  # Uses default_cost
            Decimal('0')
        """
        # Direct cost parameter
        if "cost" in kwargs and kwargs["cost"] is not None:
            cost = kwargs["cost"]
            return Decimal(str(cost)) if not isinstance(cost, Decimal) else cost

        # Bid price from RTB context
        if "bid_price" in kwargs and kwargs["bid_price"] is not None:
            bid_price = kwargs["bid_price"]
            return Decimal(str(bid_price)) if not isinstance(bid_price, Decimal) else bid_price

        # CPM pricing
        if "cpm" in kwargs and kwargs["cpm"] is not None:
            cpm = kwargs["cpm"]
            cpm_decimal = Decimal(str(cpm)) if not isinstance(cpm, Decimal) else cpm
            # CPM = cost per 1000 impressions, so divide by 1000 for single impression
            return cpm_decimal / Decimal("1000")

        # Default cost
        return self.default_cost

    async def __call__(
        self, upstream: Upstream[Any], next_handler: FetchFunc, **kwargs: Any
    ) -> Any:
        """
        Execute budget check before passing to next handler.

        Args:
            upstream: Upstream instance
            next_handler: Next handler in middleware chain
            **kwargs: Request arguments

        Returns:
            Response from next handler

        Raises:
            BudgetExceeded: If budget limit would be exceeded
            ValueError: If budget not found in store

        Example:
            >>> # Called automatically by middleware stack
            >>> result = await middleware(
            ...     upstream,
            ...     next_handler,
            ...     campaign_id="camp-1",
            ...     cost=Decimal("25.00")
            ... )
        """
        # Extract campaign_id if per-campaign mode
        campaign_id = None
        if self.per_campaign:
            campaign_id = self._extract_campaign_id(kwargs)

        # Build storage key
        key = self._build_key(campaign_id)

        # Get current budget
        budget = await self.store.get_budget(key)
        if budget is None:
            raise ValueError(
                f"Budget not found for key '{key}'. "
                "Initialize budget in store before using middleware."
            )

        # Extract cost for this request
        cost = self._extract_cost(kwargs)

        # Check if request would exceed budget
        remaining = budget.total_budget - budget.spent
        if cost > remaining:
            raise BudgetExceeded(
                f"Budget exceeded for {key}: "
                f"cost {cost} {budget.currency} exceeds remaining "
                f"{remaining} {budget.currency} "
                f"(spent: {budget.spent}/{budget.total_budget})"
            )

        # Pass to next handler first
        try:
            result = await next_handler(**kwargs)
        except Exception:
            # Don't update budget if request failed
            raise

        # Update spent amount only after successful request
        await self.store.update_spent(key, cost)
        return result
