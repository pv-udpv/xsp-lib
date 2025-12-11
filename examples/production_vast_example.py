"""Production VAST example demonstrating error tracking, caching, and metrics.

This example shows how to use the three production features together:
1. VastErrorTracker - IAB VAST 4.2 compliant error tracking with macro substitution
2. VastCacheLayer - TTL-based caching with LRU eviction and background cleanup
3. VastMetrics - Prometheus-compatible metrics for monitoring

Run with:
    python examples/production_vast_example.py

Features Demonstrated:
- Initialization and lifecycle management of all components
- Basic request flow with caching (cache miss → fetch → cache hit)
- Error tracking with multiple error scenarios and pixel firing
- Wrapper chain resolution with metrics tracking
- Cache and metrics statistics reporting
- Proper cleanup and resource management

IAB Compliance:
- Error codes per VAST 4.2 §2.4.2.2
- Error pixel macro substitution per VAST 4.2 §2.4.2.3
- Parallel error pixel firing per best practices
"""

import asyncio
import logging
import time
from typing import Any

from xsp.protocols.vast import (
    VastCacheLayer,
    VastErrorCode,
    VastErrorTracker,
    VastMetrics,
    VastUpstream,
    VastVersion,
)
from xsp.transports.memory import MemoryTransport

# Configure logging for visibility
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# Sample VAST XML responses for demonstration
SAMPLE_VAST_INLINE = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="prod-12345">
        <InLine>
            <AdSystem version="1.0">ProductionAdServer</AdSystem>
            <AdTitle>Production Test Advertisement</AdTitle>
            <Description>
                <![CDATA[Demo ad for production features showcase]]>
            </Description>
            <Error>
                <![CDATA[https://error.example.com/vast/error?code=[ERRORCODE]&ts=[TIMESTAMP]&ad=prod-12345]]>
            </Error>
            <Impression id="impression-1">
                <![CDATA[https://impression.example.com/imp?id=prod-12345&ts=[TIMESTAMP]]]>
            </Impression>
            <Impression id="impression-2">
                <![CDATA[https://backup-impression.example.com/imp?id=prod-12345]]>
            </Impression>
            <Creatives>
                <Creative id="creative-linear-1" sequence="1">
                    <Linear>
                        <Duration>00:00:30</Duration>
                        <MediaFiles>
                            <MediaFile id="media-1" delivery="progressive" type="video/mp4" 
                                       width="1920" height="1080" bitrate="5000">
                                <![CDATA[https://cdn.example.com/ads/prod-12345-1080p.mp4]]>
                            </MediaFile>
                            <MediaFile id="media-2" delivery="progressive" type="video/mp4" 
                                       width="1280" height="720" bitrate="2500">
                                <![CDATA[https://cdn.example.com/ads/prod-12345-720p.mp4]]>
                            </MediaFile>
                            <MediaFile id="media-3" delivery="progressive" type="video/mp4" 
                                       width="640" height="480" bitrate="1000">
                                <![CDATA[https://cdn.example.com/ads/prod-12345-480p.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                        <VideoClicks>
                            <ClickThrough>
                                <![CDATA[https://advertiser.example.com/landing?campaign=prod-12345]]>
                            </ClickThrough>
                            <ClickTracking>
                                <![CDATA[https://tracking.example.com/click?id=prod-12345]]>
                            </ClickTracking>
                        </VideoClicks>
                        <TrackingEvents>
                            <Tracking event="start">
                                <![CDATA[https://tracking.example.com/start?id=prod-12345]]>
                            </Tracking>
                            <Tracking event="firstQuartile">
                                <![CDATA[https://tracking.example.com/q1?id=prod-12345]]>
                            </Tracking>
                            <Tracking event="midpoint">
                                <![CDATA[https://tracking.example.com/mid?id=prod-12345]]>
                            </Tracking>
                            <Tracking event="thirdQuartile">
                                <![CDATA[https://tracking.example.com/q3?id=prod-12345]]>
                            </Tracking>
                            <Tracking event="complete">
                                <![CDATA[https://tracking.example.com/complete?id=prod-12345]]>
                            </Tracking>
                        </TrackingEvents>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""


SAMPLE_VAST_WRAPPER = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="wrapper-1">
        <Wrapper>
            <AdSystem>WrapperSystem</AdSystem>
            <VASTAdTagURI>
                <![CDATA[https://ads.example.com/vast/inline]]>
            </VASTAdTagURI>
            <Error>
                <![CDATA[https://wrapper-error.example.com/error?code=[ERRORCODE]]]>
            </Error>
            <Impression>
                <![CDATA[https://wrapper-impression.example.com/imp?id=wrapper-1]]>
            </Impression>
        </Wrapper>
    </Ad>
</VAST>"""


async def main() -> None:
    """Demonstrate production VAST features in a realistic workflow."""
    print("=" * 80)
    print("VAST PRODUCTION FEATURES DEMONSTRATION")
    print("=" * 80)
    print()
    print("This example showcases:")
    print("  • VastErrorTracker - IAB VAST 4.2 error tracking")
    print("  • VastCacheLayer - TTL-based caching with LRU eviction")
    print("  • VastMetrics - Prometheus-compatible metrics")
    print()
    print("=" * 80)
    print()

    # -------------------------------------------------------------------------
    # 1. INITIALIZATION
    # -------------------------------------------------------------------------
    print("=" * 80)
    print("1. INITIALIZING PRODUCTION COMPONENTS")
    print("=" * 80)
    print()

    # Initialize metrics
    # Note: Works with or without prometheus_client installed
    # If prometheus_client is available, metrics will be collected
    # and can be exposed via /metrics endpoint
    metrics = VastMetrics(enabled=True, namespace="vast_production")
    if metrics.enabled:
        logger.info("✓ Metrics initialized (Prometheus available)")
        print("   Metrics will be collected for Prometheus scraping")
    else:
        logger.info("✓ Metrics initialized (Prometheus not available - metrics disabled)")
        print("   Install prometheus_client to enable metrics: pip install prometheus-client")
    print()

    # Initialize cache with background cleanup
    # The cache automatically removes expired entries every 60 seconds
    cache = VastCacheLayer()
    await cache.start()
    logger.info("✓ Cache layer started with background cleanup task")
    print("   Cache configuration:")
    print(f"     - Max size: {cache.config.max_size} entries")
    print(f"     - Default TTL: {cache.config.default_ttl_seconds}s")
    print(f"     - Cleanup interval: {cache.config.cleanup_interval_seconds}s")
    print()

    # Initialize error tracker with context manager for automatic cleanup
    # The error tracker manages its own HTTP client for firing error pixels
    async with VastErrorTracker() as error_tracker:
        logger.info("✓ Error tracker initialized with HTTP client")
        print("   Error tracker configuration:")
        print(f"     - Max concurrent fires: {error_tracker.config.max_concurrent_fires}")
        print(f"     - Fire timeout: {error_tracker.config.fire_timeout_seconds}s")
        print()

        # Initialize VAST upstream with memory transport for demonstration
        # In production, you would use HttpTransport with a real ad server
        transport = MemoryTransport(SAMPLE_VAST_INLINE.encode("utf-8"))
        upstream = VastUpstream(
            transport=transport,
            endpoint="https://ads.example.com/vast",
            version=VastVersion.V4_2,
        )
        logger.info("✓ VAST upstream configured")
        print("   Upstream configuration:")
        print(f"     - Endpoint: {upstream.endpoint}")
        print(f"     - Version: VAST {upstream.version.value}")
        print()

        # -------------------------------------------------------------------------
        # 2. BASIC REQUEST WITH CACHING
        # -------------------------------------------------------------------------
        print("=" * 80)
        print("2. REQUEST FLOW WITH CACHING")
        print("=" * 80)
        print()
        await demonstrate_caching(upstream, cache, metrics)

        # -------------------------------------------------------------------------
        # 3. ERROR HANDLING AND TRACKING
        # -------------------------------------------------------------------------
        print("=" * 80)
        print("3. ERROR HANDLING AND TRACKING")
        print("=" * 80)
        print()
        await demonstrate_error_tracking(error_tracker, metrics)

        # -------------------------------------------------------------------------
        # 4. WRAPPER CHAIN RESOLUTION
        # -------------------------------------------------------------------------
        print("=" * 80)
        print("4. WRAPPER CHAIN RESOLUTION WITH METRICS")
        print("=" * 80)
        print()
        await demonstrate_wrapper_resolution(metrics)

        # -------------------------------------------------------------------------
        # 5. STATISTICS AND MONITORING
        # -------------------------------------------------------------------------
        print("=" * 80)
        print("5. STATISTICS AND MONITORING")
        print("=" * 80)
        print()
        display_statistics(cache, metrics)

        # -------------------------------------------------------------------------
        # 6. CLEANUP
        # -------------------------------------------------------------------------
        print("=" * 80)
        print("6. CLEANUP AND RESOURCE MANAGEMENT")
        print("=" * 80)
        print()

        logger.info("Closing upstream connection...")
        await upstream.close()
        print("   ✓ Upstream connection closed")

        logger.info("Stopping cache background tasks...")
        await cache.stop()
        print("   ✓ Cache cleanup task stopped")

        # Error tracker cleanup happens automatically via context manager
        print("   ✓ Error tracker HTTP client closed")
        print()

    print("=" * 80)
    print("DEMONSTRATION COMPLETE!")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("  • All three production features work seamlessly together")
    print("  • Proper lifecycle management ensures no resource leaks")
    print("  • Metrics provide observability into VAST operations")
    print("  • Caching reduces load on upstream ad servers")
    print("  • Error tracking ensures IAB VAST 4.2 compliance")
    print()


async def demonstrate_caching(
    upstream: VastUpstream, cache: VastCacheLayer, metrics: VastMetrics
) -> None:
    """Demonstrate caching with cache miss and hit scenarios.
    
    Shows:
    - Cache key generation from request parameters
    - Cache miss on first request
    - Upstream fetch with timing
    - Cache storage with TTL
    - Cache hit on second request
    - Metrics recording for both scenarios
    """
    print("Scenario: Fetch VAST ad with caching")
    print()

    # Define request parameters that would typically come from ad request
    params = {
        "user_id": "user-abc-123",
        "slot": "pre-roll",
        "width": "1920",
        "height": "1080",
        "player_version": "1.0.0",
    }

    print(f"Request parameters: {params}")
    print()

    # Generate deterministic cache key from parameters
    # The key is a SHA-256 hash of the sorted JSON representation
    cache_key = cache.generate_key(**params)
    logger.info(f"Generated cache key: {cache_key[:32]}...")
    print(f"   Cache key: {cache_key[:32]}... (truncated)")
    print()

    # -----------------------------------------------------------------------------
    # FIRST REQUEST - CACHE MISS
    # -----------------------------------------------------------------------------
    print("► First Request (expecting cache miss)")
    print()

    logger.info("Checking cache...")
    cached_response = await cache.get(cache_key)

    if cached_response is None:
        logger.info("✗ Cache miss - fetching from upstream")
        print("   ✗ Cache miss - response not in cache")
        metrics.record_cache_miss()
        print()

        # Fetch from upstream and measure duration
        print("   Fetching from upstream ad server...")
        start_time = time.time()
        xml_response = await upstream.fetch(params=params)
        duration = time.time() - start_time

        # Store in cache with 5-minute TTL
        ttl_seconds = 300
        await cache.set(cache_key, xml_response, ttl_seconds=ttl_seconds)
        logger.info(f"Stored in cache with {ttl_seconds}s TTL")
        print(f"   ✓ Response cached (TTL: {ttl_seconds}s)")

        # Record metrics
        metrics.record_request(
            upstream="production_demo",
            version="4.2",
            duration_seconds=duration,
            response_size_bytes=len(xml_response),
        )

        print(f"   ✓ Fetched {len(xml_response)} bytes in {duration*1000:.2f}ms")
        print()
    else:
        # This shouldn't happen on first request, but handle it anyway
        logger.info("✓ Cache hit!")
        print("   ✓ Cache hit (unexpected on first request)")
        metrics.record_cache_hit()
        print()

    # -----------------------------------------------------------------------------
    # SECOND REQUEST - CACHE HIT
    # -----------------------------------------------------------------------------
    print("► Second Request (expecting cache hit)")
    print()

    logger.info("Checking cache...")
    start_time = time.time()
    cached_response = await cache.get(cache_key)
    cache_duration = time.time() - start_time

    if cached_response:
        logger.info("✓ Cache hit - served from cache")
        print("   ✓ Cache hit - response served from cache")
        metrics.record_cache_hit()
        print(f"   ✓ Served {len(cached_response)} bytes in {cache_duration*1000:.2f}ms")
        print()
        print(f"   Performance improvement: ~{(duration/cache_duration):.1f}x faster than upstream fetch")
        print()
    else:
        logger.warning("✗ Cache miss (unexpected on second request)")
        print("   ✗ Cache miss (unexpected on second request)")
        metrics.record_cache_miss()
        print()

    # Show cache statistics after operations
    stats = cache.get_stats()
    print("Cache Statistics After Requests:")
    print(f"   • Total requests: {stats.hits + stats.misses}")
    print(f"   • Hits: {stats.hits}")
    print(f"   • Misses: {stats.misses}")
    print(f"   • Hit rate: {stats.hit_rate * 100:.1f}%")
    print()


async def demonstrate_error_tracking(
    error_tracker: VastErrorTracker, metrics: VastMetrics
) -> None:
    """Demonstrate error tracking with various IAB VAST 4.2 error codes.
    
    Shows:
    - Different error scenarios (XML parsing, wrapper timeout, file not found)
    - Error pixel URLs with VAST macros
    - Macro substitution ([ERRORCODE], [TIMESTAMP])
    - Parallel error pixel firing
    - Error metrics recording
    """
    print("Scenario: Track various VAST errors with pixel firing")
    print()
    print("IAB VAST 4.2 defines standardized error codes for different failure scenarios.")
    print("Error pixels notify ad servers and allow tracking of delivery issues.")
    print()

    # Example error URLs with VAST macros (per VAST 4.2 §2.4.2.3)
    # [ERRORCODE] - substituted with numeric error code
    # [TIMESTAMP] - substituted with Unix timestamp in milliseconds
    error_urls = [
        "https://error.example.com/vast?code=[ERRORCODE]&ts=[TIMESTAMP]",
        "https://backup-error.example.com/track?error=[ERRORCODE]&time=[TIMESTAMP]",
    ]

    print(f"Error tracking URLs configured: {len(error_urls)}")
    for i, url in enumerate(error_urls, 1):
        print(f"   {i}. {url}")
    print()

    # Define error scenarios to demonstrate
    error_scenarios = [
        (
            VastErrorCode.XML_PARSING_ERROR,
            "XML Parsing Error",
            "Invalid or malformed VAST XML response",
        ),
        (
            VastErrorCode.WRAPPER_TIMEOUT,
            "Wrapper Timeout",
            "Wrapper chain resolution exceeded timeout limit",
        ),
        (
            VastErrorCode.FILE_NOT_FOUND,
            "File Not Found",
            "Media file URL returned 404 error",
        ),
    ]

    # Track each error scenario
    for error_code, error_name, description in error_scenarios:
        print(f"► Error Scenario: {error_name} (Code {error_code.value})")
        print(f"   Description: {description}")
        print()

        # Track error - this fires all error pixels in parallel
        logger.info(f"Tracking error: {error_name} (code {error_code.value})")
        await error_tracker.track_error(
            error_code=error_code,
            error_urls=error_urls,
            additional_context={
                "description": description,
                "scenario": "production_demo",
            },
        )

        # Record metrics
        metrics.record_error(error_code.value, error_code.name)
        metrics.record_error_pixel_fired(len(error_urls))

        print(f"   ✓ Error tracked and {len(error_urls)} pixels fired")
        print()

        # Show example of macro substitution
        example_url = error_urls[0]
        substituted = example_url.replace("[ERRORCODE]", str(error_code.value))
        substituted = substituted.replace("[TIMESTAMP]", str(int(time.time() * 1000)))
        print(f"   Example substituted URL:")
        print(f"   {substituted}")
        print()

    print("Error Tracking Summary:")
    print(f"   • Total errors tracked: {len(error_scenarios)}")
    print(f"   • Total pixels fired: {len(error_scenarios) * len(error_urls)}")
    print(f"   • All pixels fired in parallel for optimal performance")
    print()


async def demonstrate_wrapper_resolution(metrics: VastMetrics) -> None:
    """Demonstrate wrapper chain resolution with metrics tracking.
    
    Shows:
    - Wrapper chain concept (wrapper → wrapper → inline)
    - Chain depth tracking
    - Resolution duration metrics
    - Wrapper resolution best practices
    """
    print("Scenario: VAST wrapper chain resolution")
    print()
    print("VAST wrappers allow ad servers to redirect to other VAST responses,")
    print("creating chains that must be resolved to reach the final inline ad.")
    print()

    # Simulate wrapper chain resolution
    # In production, this would be done by VastChainResolver
    print("Simulating wrapper chain resolution:")
    print()

    chain_depth = 3
    print(f"   Wrapper Chain Depth: {chain_depth}")
    print("   ┌─────────────┐")
    print("   │  Wrapper 1  │ (depth 1)")
    print("   └──────┬──────┘")
    print("          │ VASTAdTagURI")
    print("          ▼")
    print("   ┌─────────────┐")
    print("   │  Wrapper 2  │ (depth 2)")
    print("   └──────┬──────┘")
    print("          │ VASTAdTagURI")
    print("          ▼")
    print("   ┌─────────────┐")
    print("   │   Inline    │ (depth 3 - terminal)")
    print("   └─────────────┘")
    print()

    # Simulate resolution timing
    print("   Resolving chain...")
    start_time = time.time()
    await asyncio.sleep(0.1)  # Simulate network latency
    resolution_duration = time.time() - start_time

    # Record chain resolution metrics
    metrics.record_chain_resolution(depth=chain_depth, duration_seconds=resolution_duration)

    print(f"   ✓ Chain resolved in {resolution_duration*1000:.2f}ms")
    print()

    print("Wrapper Resolution Best Practices:")
    print("   • VAST 4.2 recommends max wrapper depth of 5 (§2.4.3.4)")
    print("   • Track resolution time to identify slow chains")
    print("   • Implement timeout protection (typically 5-10 seconds)")
    print("   • Cache resolved chains to reduce latency")
    print("   • Fire error pixels if wrapper limit is exceeded")
    print()


def display_statistics(cache: VastCacheLayer, metrics: VastMetrics) -> None:
    """Display comprehensive statistics from cache and metrics.
    
    Shows:
    - Cache hit/miss rates
    - Cache size and evictions
    - Metrics collection status
    - Prometheus integration guidance
    """
    print("Production Metrics and Statistics")
    print()

    # -----------------------------------------------------------------------------
    # CACHE STATISTICS
    # -----------------------------------------------------------------------------
    stats = cache.get_stats()

    print("► Cache Performance:")
    print()
    total_requests = stats.hits + stats.misses
    if total_requests > 0:
        print(f"   Total Requests:     {total_requests:,}")
        print(f"   Cache Hits:         {stats.hits:,}")
        print(f"   Cache Misses:       {stats.misses:,}")
        print(f"   Hit Rate:           {stats.hit_rate * 100:.1f}%")
        print()
        print(f"   Current Size:       {stats.size:,} entries")
        print(f"   Total Evictions:    {stats.evictions:,}")
        print()

        # Calculate cache efficiency metrics
        if stats.hit_rate >= 0.8:
            efficiency = "Excellent"
        elif stats.hit_rate >= 0.6:
            efficiency = "Good"
        elif stats.hit_rate >= 0.4:
            efficiency = "Fair"
        else:
            efficiency = "Poor"

        print(f"   Cache Efficiency:   {efficiency}")
        print()

    # Update metrics gauge with current cache size
    metrics.update_cache_size(stats.size)

    # -----------------------------------------------------------------------------
    # METRICS SYSTEM STATUS
    # -----------------------------------------------------------------------------
    print("► Metrics Collection:")
    print()

    if metrics.enabled:
        print("   Status:             Enabled ✓")
        print("   Backend:            Prometheus")
        print()
        print("   Available Metrics:")
        print("     • vast_production_requests_total (Counter)")
        print("     • vast_production_request_duration_seconds (Histogram)")
        print("     • vast_production_response_size_bytes (Histogram)")
        print("     • vast_production_errors_total (Counter)")
        print("     • vast_production_error_pixels_fired_total (Counter)")
        print("     • vast_production_cache_hits_total (Counter)")
        print("     • vast_production_cache_misses_total (Counter)")
        print("     • vast_production_cache_size (Gauge)")
        print("     • vast_production_cache_evictions_total (Counter)")
        print("     • vast_production_chain_depth (Histogram)")
        print("     • vast_production_chain_resolution_duration_seconds (Histogram)")
        print()
        print("   Integration:")
        print("     Expose metrics endpoint in your application:")
        print()
        print("     ```python")
        print("     from prometheus_client import start_http_server")
        print("     ")
        print("     # Start metrics server on port 8000")
        print("     start_http_server(8000)")
        print("     ")
        print("     # Metrics available at: http://localhost:8000/metrics")
        print("     ```")
        print()
    else:
        print("   Status:             Disabled")
        print("   Reason:             prometheus_client not installed")
        print()
        print("   To Enable:")
        print("     pip install prometheus-client")
        print()

    # -----------------------------------------------------------------------------
    # PRODUCTION RECOMMENDATIONS
    # -----------------------------------------------------------------------------
    print("► Production Recommendations:")
    print()
    print("   1. Monitoring:")
    print("      • Set up Prometheus to scrape /metrics endpoint")
    print("      • Configure Grafana dashboards for visualization")
    print("      • Set alerts for high error rates and low cache hit rates")
    print()
    print("   2. Cache Tuning:")
    print("      • Adjust max_size based on available memory")
    print("      • Tune TTL based on ad server freshness requirements")
    print("      • Monitor eviction rate to prevent premature evictions")
    print()
    print("   3. Error Handling:")
    print("      • Implement retry logic with exponential backoff")
    print("      • Set up dead letter queue for failed error pixels")
    print("      • Monitor error pixel fire success rates")
    print()
    print("   4. Performance:")
    print("      • Use connection pooling for HTTP client")
    print("      • Consider distributed caching (Redis) for multi-instance deployments")
    print("      • Implement circuit breakers for upstream failures")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("Demonstration interrupted by user")
    except Exception as e:
        logger.error(f"Demonstration failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
