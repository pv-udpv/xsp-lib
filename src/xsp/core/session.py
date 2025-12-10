"""
Session management for stateful ad serving.

This module provides abstractions for managing stateful sessions in xsp-lib:
- SessionContext: Immutable context shared across wrapper resolution chains
- UpstreamSession: Protocol for stateful ad serving with frequency capping and budget tracking

Per VAST 4.2 §2.4.2.5, session context maintains correlator and timestamp
macros across wrapper resolution chains.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SessionContext:
    """
    Immutable session context shared across wrapper resolution chain.
    
    SessionContext maintains consistent values for VAST macros and tracking
    across multiple upstream requests within a single ad serving session.
    
    Per VAST 4.2 §2.4.2.5, macro values like [TIMESTAMP] and [CORRELATOR]
    must remain constant throughout wrapper resolution.
    
    Attributes:
        timestamp: Unix timestamp in milliseconds (for [TIMESTAMP] macro)
        correlator: Unique session ID (for [CORRELATOR] macro)
        cachebusting: Random value (for [CACHEBUSTING] macro)
        cookies: HTTP cookies to preserve across requests
        request_id: Request tracing ID for debugging
    
    Example:
        ```python
        import time
        from xsp.core.session import SessionContext
        
        # Create immutable session context
        context = SessionContext(
            timestamp=int(time.time() * 1000),
            correlator="session-abc123",
            cachebusting="rand-456789",
            cookies={"uid": "user123"},
            request_id="req-001"
        )
        
        # Context is immutable - this raises FrozenInstanceError
        # context.timestamp = 9999  # ❌ Error
        
        # Use with upstream session
        session = await upstream.create_session(context)
        ```
    
    References:
        - VAST 4.2 §2.4.2.5 (Macro substitution)
        - OpenRTB 2.6 §3.2.18 (User tracking)
    """
    
    timestamp: int
    correlator: str
    cachebusting: str
    cookies: dict[str, str]
    request_id: str


class UpstreamSession(Protocol):
    """
    Stateful session for ad serving with frequency capping and budget tracking.
    
    UpstreamSession provides a protocol for implementing stateful ad serving
    sessions that maintain state across multiple requests. This enables:
    - Frequency capping enforcement
    - Budget tracking and spend limits
    - Session-scoped macro values (correlator, timestamp)
    - Cookie preservation across wrapper resolution
    
    Example:
        ```python
        import asyncio
        from xsp.core.session import SessionContext, UpstreamSession
        from xsp.protocols.vast import VastUpstream
        from xsp.transports.http import HttpTransport
        
        async def serve_ad_with_frequency_cap():
            # Create upstream
            transport = HttpTransport()
            upstream = VastUpstream(transport, "https://ads.example.com/vast")
            
            # Create session
            context = SessionContext(
                timestamp=int(time.time() * 1000),
                correlator="session-abc123",
                cachebusting="rand-456789",
                cookies={},
                request_id="req-001"
            )
            
            session = await upstream.create_session(context)
            
            # Check frequency cap before serving
            if await session.check_frequency_cap("user123"):
                response = await session.request(params={"slot": "pre-roll"})
                print(f"Served ad: {len(response)} bytes")
                
                # Track budget spend
                await session.track_budget("campaign-456", 2.50)
            else:
                print("Frequency cap exceeded")
            
            await session.close()
        
        asyncio.run(serve_ad_with_frequency_cap())
        ```
    
    References:
        - VAST 4.2 §2.4.3.4 (Wrapper resolution with consistent macros)
        - OpenRTB 2.6 §4.1 (Frequency capping)
        - IAB Frequency Capping Guidelines
    """
    
    @property
    def context(self) -> SessionContext:
        """
        Get immutable session context.
        
        Returns:
            SessionContext with correlator, timestamp, and other values
        """
        ...
    
    async def request(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Send request within session context.
        
        SessionContext values (correlator, timestamp, cookies) are
        automatically applied to all requests in the session.
        
        Args:
            params: Request parameters
            headers: HTTP headers (merged with session cookies)
            **kwargs: Additional protocol-specific arguments
        
        Returns:
            Response data (e.g., VAST XML, OpenRTB JSON)
        
        Raises:
            XspError: On request failure
        
        Example:
            ```python
            # Request with session context applied
            xml = await session.request(
                params={"slot": "pre-roll", "w": 640, "h": 480}
            )
            ```
        """
        ...
    
    async def check_frequency_cap(self, user_id: str) -> bool:
        """
        Check if user has exceeded frequency cap.
        
        Frequency capping limits how many times a user sees ads from
        a campaign within a time window (e.g., max 3 impressions per day).
        
        Args:
            user_id: User identifier (e.g., cookie ID, device ID)
        
        Returns:
            True if ad can be served (under cap), False if cap exceeded
        
        Example:
            ```python
            if await session.check_frequency_cap("user123"):
                # Serve ad
                xml = await session.request(params={...})
            else:
                # Serve backup/filler ad
                xml = await fallback_upstream.request(params={...})
            ```
        
        References:
            - IAB Frequency Capping Guidelines
            - OpenRTB 2.6 §4.1 (User-level capping)
        """
        ...
    
    async def track_budget(self, campaign_id: str, amount: float) -> None:
        """
        Track budget spend for campaign.
        
        Budget tracking enforces campaign spend limits by recording
        the cost of each ad impression or click.
        
        Args:
            campaign_id: Campaign identifier
            amount: Amount spent (e.g., CPM cost in currency units)
        
        Raises:
            XspError: If budget tracking fails
        
        Example:
            ```python
            # After successful ad impression
            await session.track_budget(
                campaign_id="campaign-456",
                amount=2.50  # $2.50 CPM
            )
            ```
        
        References:
            - OpenRTB 2.6 §3.2.4 (Budget management)
        """
        ...
    
    async def close(self) -> None:
        """
        Release session resources.
        
        Should be called when session is complete to clean up state
        backend connections, cache entries, etc.
        
        Example:
            ```python
            session = await upstream.create_session(context)
            try:
                xml = await session.request(params={...})
            finally:
                await session.close()
            ```
        """
        ...
