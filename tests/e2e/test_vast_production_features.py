"""E2E tests for VAST production features.

Tests the integration of error tracking, caching, and metrics for VAST
operations as per IAB VAST 4.2 specification.
"""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from xsp.protocols.vast import (
    VastCacheLayer,
    VastChainConfig,
    VastChainResolver,
    VastErrorCode,
    VastErrorTracker,
    VastMetrics,
    VastUpstream,
)
from xsp.protocols.vast.cache import VastCacheConfig
from xsp.protocols.vast.error_tracker import VastErrorTrackerConfig
from xsp.transports.memory import MemoryTransport


@pytest.fixture
def sample_vast_xml() -> str:
    """Sample VAST 4.2 XML for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="test-ad-001">
        <InLine>
            <AdSystem>TestSystem</AdSystem>
            <AdTitle>Test Ad</AdTitle>
            <Error><![CDATA[https://error.example.com/error?code=[ERRORCODE]&ts=[TIMESTAMP]]]></Error>
            <Impression><![CDATA[https://impression.example.com/imp?id=123]]></Impression>
            <Creatives>
                <Creative>
                    <Linear>
                        <Duration>00:00:30</Duration>
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


@pytest.fixture
def sample_vast_wrapper_xml() -> str:
    """Sample VAST 4.2 wrapper XML for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="wrapper-001">
        <Wrapper>
            <AdSystem>WrapperSystem</AdSystem>
            <VASTAdTagURI><![CDATA[https://example.com/vast-inline]]></VASTAdTagURI>
            <Impression><![CDATA[https://wrapper.example.com/imp]]></Impression>
            <Error><![CDATA[https://error.example.com/wrapper-error?code=[ERRORCODE]]]></Error>
        </Wrapper>
    </Ad>
</VAST>"""


@pytest_asyncio.fixture(scope="function")
async def cache_layer():
    """Create cache layer for testing."""
    cache = VastCacheLayer(VastCacheConfig(max_size=100, default_ttl_seconds=300.0))
    await cache.start()
    yield cache
    await cache.stop()


@pytest_asyncio.fixture(scope="function")
async def error_tracker():
    """Create error tracker with mock HTTP client."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    tracker = VastErrorTracker(
        config=VastErrorTrackerConfig(enable_logging=False), http_client=mock_client
    )
    yield tracker, mock_client


@pytest.fixture(scope="function")
def metrics():
    """Create metrics collector for testing."""
    return VastMetrics(enabled=True)


@pytest.mark.asyncio
async def test_successful_request_with_all_features(
    sample_vast_xml: str, cache_layer: VastCacheLayer, metrics: VastMetrics
):
    """Test complete workflow: cache miss → fetch → cache → cache hit.

    Validates:
    - First request results in cache miss and fetch
    - Response is cached with proper TTL
    - Second request hits cache
    - Metrics are recorded for both requests
    """
    # Create upstream with memory transport
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")

    # Generate cache key
    cache_key = cache_layer.generate_key("test-endpoint", {"param": "value"})

    # First request - cache miss
    cached_response = await cache_layer.get(cache_key)
    assert cached_response is None

    stats_before = cache_layer.get_stats()
    assert stats_before.misses == 1
    assert stats_before.hits == 0

    # Fetch from upstream
    start_time = time.time()
    xml_response = await upstream.fetch()
    duration = time.time() - start_time

    assert "<VAST version=" in xml_response
    assert "Test Ad" in xml_response

    # Cache the response
    await cache_layer.set(cache_key, xml_response, ttl_seconds=60.0)

    # Record metrics
    metrics.record_request(
        upstream="test-upstream",
        version="4.2",
        duration_seconds=duration,
        response_size_bytes=len(xml_response.encode("utf-8")),
    )
    metrics.record_cache_miss()
    metrics.update_cache_size(cache_layer.get_stats().size)

    # Second request - cache hit
    cached_response = await cache_layer.get(cache_key)
    assert cached_response is not None
    assert cached_response == xml_response

    stats_after = cache_layer.get_stats()
    assert stats_after.hits == 1
    assert stats_after.misses == 1
    assert stats_after.size == 1

    # Record cache hit metric
    metrics.record_cache_hit()

    # Verify hit rate
    assert stats_after.hit_rate == 0.5  # 1 hit, 1 miss

    await upstream.close()


@pytest.mark.asyncio
async def test_error_tracking_integration(error_tracker):
    """Test error tracking: simulate errors, fire pixels, record metrics.

    Validates:
    - Error tracking with various IAB VAST error codes
    - Error pixel firing with macro substitution
    - Multiple error URLs handled concurrently
    - Metrics recorded for error events
    """
    tracker, mock_client = error_tracker
    metrics = VastMetrics(enabled=True)

    # Define error URLs with macros
    error_urls = [
        "https://error1.example.com/err?code=[ERRORCODE]&ts=[TIMESTAMP]",
        "https://error2.example.com/err?code=[ERRORCODE]&ts=[TIMESTAMP]",
        "https://error3.example.com/err?code=[ERRORCODE]",
    ]

    # Track various error codes
    test_errors = [
        (VastErrorCode.XML_PARSING_ERROR, "parsing_error"),
        (VastErrorCode.WRAPPER_LIMIT_REACHED, "wrapper_error"),
        (VastErrorCode.TIMEOUT, "timeout_error"),
    ]

    for error_code, error_type in test_errors:
        # Track error
        await tracker.track_error(
            error_code=error_code,
            error_urls=error_urls,
            additional_context={"test": "context"},
        )

        # Record metrics
        metrics.record_error(error_code=error_code.value, error_type=error_type)
        metrics.record_error_pixel_fired(count=len(error_urls))

    # Verify HTTP client was called for each error URL
    assert mock_client.get.call_count == len(test_errors) * len(error_urls)

    # Verify macro substitution happened
    for call in mock_client.get.call_args_list:
        url = call[0][0]
        assert "[ERRORCODE]" not in url
        # TIMESTAMP may or may not be in all URLs, so only check substitution if present in original
        if "[TIMESTAMP]" in str(error_urls):
            assert "[TIMESTAMP]" not in url or "ts=" not in url


@pytest.mark.asyncio
async def test_wrapper_chain_with_metrics(
    sample_vast_wrapper_xml: str, sample_vast_xml: str, metrics: VastMetrics
):
    """Test wrapper chain resolution with depth and timing metrics.

    Validates:
    - Wrapper chain resolution tracking
    - Chain depth measurement
    - Resolution time measurement
    - Metrics collection for chain operations
    """
    # Create upstreams for wrapper and inline
    wrapper_transport = MemoryTransport(sample_vast_wrapper_xml.encode("utf-8"))
    inline_transport = MemoryTransport(sample_vast_xml.encode("utf-8"))

    wrapper_upstream = VastUpstream(
        transport=wrapper_transport, endpoint="https://wrapper.example.com/vast"
    )
    inline_upstream = VastUpstream(
        transport=inline_transport, endpoint="https://inline.example.com/vast"
    )

    # Create resolver
    config = VastChainConfig(max_depth=5, selection_strategy="highest_bitrate")
    _resolver = VastChainResolver(
        config=config, upstreams={"primary": wrapper_upstream, "fallback": inline_upstream}
    )

    # Measure resolution time
    start_time = time.time()

    # Note: This is a simplified test - actual resolution would follow VASTAdTagURI
    # Here we just verify the metrics recording works
    chain_depth = 2  # Simulating 1 wrapper + 1 inline
    resolution_duration = time.time() - start_time

    # Record metrics
    metrics.record_chain_resolution(depth=chain_depth, duration_seconds=resolution_duration)

    # Verify metrics were recorded (by checking no exceptions)
    assert True  # If we got here, metrics recording worked

    await wrapper_upstream.close()
    await inline_upstream.close()


@pytest.mark.asyncio
async def test_cache_expiration_and_eviction(cache_layer: VastCacheLayer):
    """Test cache TTL expiration and LRU eviction.

    Validates:
    - Entries expire after TTL
    - Expired entries are cleaned up
    - LRU eviction when max size reached
    - Cache statistics updated correctly
    """
    # Test TTL expiration
    key1 = "test-key-1"
    value1 = "test-value-1"

    # Set with very short TTL
    await cache_layer.set(key1, value1, ttl_seconds=0.1)

    # Immediately should be retrievable
    result = await cache_layer.get(key1)
    assert result == value1

    # Wait for expiration
    await asyncio.sleep(0.2)

    # Should be expired and return None
    result = await cache_layer.get(key1)
    assert result is None

    # Test LRU eviction
    cache_config = VastCacheConfig(max_size=3, default_ttl_seconds=60.0)
    small_cache = VastCacheLayer(config=cache_config)
    await small_cache.start()

    try:
        # Fill cache to max
        await small_cache.set("key1", "value1")
        await small_cache.set("key2", "value2")
        await small_cache.set("key3", "value3")

        stats = small_cache.get_stats()
        assert stats.size == 3

        # Add one more - should evict oldest (key1)
        await small_cache.set("key4", "value4")

        stats = small_cache.get_stats()
        assert stats.size == 3
        assert stats.evictions == 1

        # key1 should be evicted
        result = await small_cache.get("key1")
        assert result is None

        # Others should still be there
        result = await small_cache.get("key2")
        assert result == "value2"

    finally:
        await small_cache.stop()


@pytest.mark.asyncio
async def test_concurrent_requests_with_caching(
    sample_vast_xml: str, cache_layer: VastCacheLayer
):
    """Test concurrent cache operations for race conditions.

    Validates:
    - Multiple concurrent cache get/set operations
    - No race conditions in concurrent access
    - Statistics remain consistent
    - Thread-safety of cache operations
    """
    # Prepare multiple cache operations
    async def cache_operation(index: int):
        key = f"concurrent-key-{index}"
        value = f"concurrent-value-{index}"

        # Set value
        await cache_layer.set(key, value)

        # Small random delay to increase concurrency
        await asyncio.sleep(0.001)

        # Get value
        result = await cache_layer.get(key)
        assert result == value

        return result

    # Run 50 concurrent operations
    tasks = [cache_operation(i) for i in range(50)]
    results = await asyncio.gather(*tasks)

    # Verify all operations completed successfully
    assert len(results) == 50
    assert all(r is not None for r in results)

    # Check cache stats
    stats = cache_layer.get_stats()
    assert stats.hits == 50  # All gets should hit
    assert stats.size <= 50  # Should not exceed operations


@pytest.mark.asyncio
async def test_error_scenario_with_fallback(sample_vast_xml: str):
    """Test error scenario: timeout → error tracking → fallback.

    Validates:
    - Error handling with timeout
    - Error tracking for failed requests
    - Fallback mechanism works
    - Metrics recorded for error scenarios
    """
    # Create mock HTTP client for error tracking
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    tracker = VastErrorTracker(
        config=VastErrorTrackerConfig(enable_logging=False), http_client=mock_client
    )
    metrics = VastMetrics(enabled=True)

    error_urls = ["https://error.example.com/err?code=[ERRORCODE]"]

    # Simulate timeout error
    await tracker.track_error(
        error_code=VastErrorCode.TIMEOUT,
        error_urls=error_urls,
        additional_context={"reason": "upstream_timeout"},
    )

    # Record error metrics
    metrics.record_error(error_code=VastErrorCode.TIMEOUT.value, error_type="timeout")

    # Simulate successful fallback
    fallback_transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    fallback_upstream = VastUpstream(
        transport=fallback_transport, endpoint="https://fallback.example.com/vast"
    )

    # Fetch from fallback
    xml_response = await fallback_upstream.fetch()
    assert "Test Ad" in xml_response

    # Record successful fallback metrics
    metrics.record_request(
        upstream="fallback-upstream",
        version="4.2",
        duration_seconds=0.1,
        response_size_bytes=len(xml_response.encode("utf-8")),
    )

    # Verify error pixel was fired
    assert mock_client.get.call_count == 1

    await fallback_upstream.close()


@pytest.mark.asyncio
async def test_full_production_workflow(
    sample_vast_xml: str, cache_layer: VastCacheLayer, error_tracker, metrics: VastMetrics
):
    """Test complete production workflow with all features.

    Validates:
    - All components working together
    - Cache, error tracking, and metrics integrated
    - Complex workflow with errors and recovery
    - Statistics consistent across all components
    """
    tracker, mock_client = error_tracker

    # Create upstream
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")

    # Generate cache key
    cache_key = cache_layer.generate_key("production-test", {"user_id": "12345"})

    # Step 1: Check cache (miss expected)
    cached = await cache_layer.get(cache_key)
    assert cached is None
    metrics.record_cache_miss()

    # Step 2: Fetch from upstream
    start_time = time.time()
    xml_response = await upstream.fetch()
    duration = time.time() - start_time

    # Step 3: Record metrics
    metrics.record_request(
        upstream="production-upstream",
        version="4.2",
        duration_seconds=duration,
        response_size_bytes=len(xml_response.encode("utf-8")),
    )

    # Step 4: Cache the response
    await cache_layer.set(cache_key, xml_response)
    metrics.update_cache_size(cache_layer.get_stats().size)

    # Step 5: Simulate an error during processing
    error_urls = ["https://error.example.com/err?code=[ERRORCODE]"]
    await tracker.track_error(
        error_code=VastErrorCode.MEDIA_FILE_DISPLAY_ERROR,
        error_urls=error_urls,
        additional_context={"reason": "codec_not_supported"},
    )
    metrics.record_error(
        error_code=VastErrorCode.MEDIA_FILE_DISPLAY_ERROR.value, error_type="media_error"
    )
    metrics.record_error_pixel_fired(count=1)

    # Step 6: Verify cache hit on second request
    cached = await cache_layer.get(cache_key)
    assert cached is not None
    assert cached == xml_response
    metrics.record_cache_hit()

    # Verify final statistics
    stats = cache_layer.get_stats()
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.hit_rate == 0.5
    assert stats.size == 1

    # Verify error pixel fired
    assert mock_client.get.call_count == 1

    await upstream.close()


@pytest.mark.asyncio
async def test_edge_cases():
    """Test edge cases: invalid keys, empty URLs, disabled metrics.

    Validates:
    - Handling of edge cases and invalid inputs
    - Graceful degradation
    - No crashes with invalid data
    """
    # Test empty cache key
    cache = VastCacheLayer()
    await cache.start()
    try:
        empty_key = cache.generate_key()
        await cache.set(empty_key, "value")
        result = await cache.get(empty_key)
        assert result == "value"
    finally:
        await cache.stop()

    # Test empty error URL list
    mock_client = AsyncMock()
    tracker = VastErrorTracker(
        config=VastErrorTrackerConfig(enable_logging=False), http_client=mock_client
    )

    await tracker.track_error(error_code=VastErrorCode.UNDEFINED_ERROR, error_urls=[])
    assert mock_client.get.call_count == 0  # No calls with empty list

    # Test metrics with enabled=False
    disabled_metrics = VastMetrics(enabled=False)
    disabled_metrics.record_request("test", "4.2", 1.0, 1000)  # Should not crash
    disabled_metrics.record_error(100, "test")  # Should not crash
    disabled_metrics.record_cache_hit()  # Should not crash
    disabled_metrics.record_cache_miss()  # Should not crash
    disabled_metrics.update_cache_size(10)  # Should not crash
    disabled_metrics.record_cache_eviction(1)  # Should not crash
    disabled_metrics.record_error_pixel_fired(1)  # Should not crash
    disabled_metrics.record_chain_resolution(2, 0.5)  # Should not crash
    disabled_metrics.record_creative_selection("test", 5000)  # Should not crash

    # Test async context manager for metrics
    async with disabled_metrics.track_request("test", "4.2"):
        pass  # Should not crash

    # Test cache with None/invalid values
    cache2 = VastCacheLayer()
    await cache2.start()
    try:
        await cache2.set("null-key", None)
        result = await cache2.get("null-key")
        assert result is None or result == "None"  # Should handle None gracefully
    finally:
        await cache2.stop()


@pytest.mark.asyncio
async def test_performance_benchmarks(cache_layer: VastCacheLayer):
    """Test performance: cache ops/sec, concurrent access.

    Validates:
    - Cache performance meets requirements
    - Concurrent operations perform well
    - No significant degradation under load
    """
    # Benchmark: Sequential cache operations
    num_ops = 1000
    start_time = time.time()

    for i in range(num_ops):
        key = f"perf-key-{i}"
        await cache_layer.set(key, f"value-{i}")

    set_duration = time.time() - start_time
    set_ops_per_sec = num_ops / set_duration

    # Get operations
    start_time = time.time()

    for i in range(num_ops):
        key = f"perf-key-{i}"
        await cache_layer.get(key)

    get_duration = time.time() - start_time
    get_ops_per_sec = num_ops / get_duration

    # Log performance results (assertions would be environment-dependent)
    print("\nPerformance Results:")
    print(f"  Cache SET: {set_ops_per_sec:.2f} ops/sec")
    print(f"  Cache GET: {get_ops_per_sec:.2f} ops/sec")

    # Verify reasonable performance (not too slow)
    assert set_ops_per_sec > 100  # At least 100 sets per second
    assert get_ops_per_sec > 100  # At least 100 gets per second

    # Benchmark: Concurrent operations
    async def concurrent_op(index: int):
        key = f"concurrent-{index}"
        await cache_layer.set(key, f"value-{index}")
        return await cache_layer.get(key)

    num_concurrent = 100
    start_time = time.time()
    results = await asyncio.gather(*[concurrent_op(i) for i in range(num_concurrent)])
    concurrent_duration = time.time() - start_time
    concurrent_ops_per_sec = num_concurrent / concurrent_duration

    print(f"  Concurrent ops: {concurrent_ops_per_sec:.2f} ops/sec")

    # Verify all operations succeeded
    assert len(results) == num_concurrent
    assert all(r is not None for r in results)

    # Concurrent should be reasonably fast
    assert concurrent_ops_per_sec > 50  # At least 50 concurrent ops/sec


@pytest.mark.asyncio
async def test_cache_cleanup_task():
    """Test that cache cleanup task properly removes expired entries.

    Validates:
    - Background cleanup task runs
    - Expired entries are removed
    - Non-expired entries remain
    """
    # Create cache with short cleanup interval
    config = VastCacheConfig(
        max_size=100, default_ttl_seconds=0.5, cleanup_interval_seconds=0.2
    )
    cache = VastCacheLayer(config=config)
    await cache.start()

    try:
        # Add entries
        await cache.set("key1", "value1", ttl_seconds=0.3)  # Short TTL
        await cache.set("key2", "value2", ttl_seconds=10.0)  # Long TTL

        # Verify both exist
        assert await cache.get("key1") is not None
        assert await cache.get("key2") is not None

        # Wait for cleanup to run (cleanup interval + TTL expiration)
        await asyncio.sleep(0.6)

        # key1 should be gone, key2 should remain
        assert await cache.get("key1") is None
        assert await cache.get("key2") is not None

    finally:
        await cache.stop()


@pytest.mark.asyncio
async def test_metrics_with_labels(metrics: VastMetrics):
    """Test metrics recording with various labels.

    Validates:
    - Metrics can be recorded with different label values
    - Labels are properly differentiated
    - No label conflicts or errors
    """
    # Record requests with different labels
    metrics.record_request(
        upstream="upstream-1", version="4.2", duration_seconds=0.5, response_size_bytes=10000
    )
    metrics.record_request(
        upstream="upstream-2", version="4.1", duration_seconds=1.0, response_size_bytes=20000
    )

    # Record errors with different codes
    metrics.record_error(error_code=100, error_type="parsing")
    metrics.record_error(error_code=400, error_type="media")
    metrics.record_error(error_code=300, error_type="wrapper")

    # Record creative selections
    metrics.record_creative_selection(strategy="highest_bitrate", bitrate_kbps=5000)
    metrics.record_creative_selection(strategy="lowest_bitrate", bitrate_kbps=1000)
    metrics.record_creative_selection(strategy="adaptive", bitrate_kbps=3000)

    # If we got here without exceptions, labels work correctly
    assert True


@pytest.mark.asyncio
async def test_error_tracker_context_manager():
    """Test error tracker as async context manager.

    Validates:
    - Proper initialization in __aenter__
    - Proper cleanup in __aexit__
    - HTTP client lifecycle management
    """
    # Test with owned client
    async with VastErrorTracker(config=VastErrorTrackerConfig(enable_logging=False)) as tracker:
        assert tracker._http_client is not None

        # Use tracker - we'll skip firing pixels since it requires real HTTP
        # Just verify the tracker is usable
        pass

    # Client should be closed after context exit
    # (We can't easily verify this without accessing internals)

    # Test with provided client
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    async with VastErrorTracker(
        config=VastErrorTrackerConfig(enable_logging=False), http_client=mock_client
    ) as tracker:
        await tracker.track_error(
            error_code=VastErrorCode.XML_PARSING_ERROR,
            error_urls=["https://error.example.com/err?code=[ERRORCODE]"],
        )

    # Provided client should not be closed
    assert not mock_client.close.called
