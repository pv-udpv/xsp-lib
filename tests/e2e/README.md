# E2E Tests for xsp-lib

This directory contains end-to-end (E2E) tests that validate complete workflows and integration between multiple components.

## VAST Production Features E2E Tests

**File:** `test_vast_production_features.py`

Comprehensive E2E tests for VAST production features including error tracking, caching, and metrics integration per IAB VAST 4.2 specification.

### Test Coverage

| Module | Coverage | Notes |
|--------|----------|-------|
| `xsp.protocols.vast.cache` | 94% | TTL-based caching with LRU eviction |
| `xsp.protocols.vast.error_tracker` | 92% | IAB VAST error tracking and pixel firing |
| `xsp.protocols.vast.metrics` | 65% | Prometheus metrics (some paths require prometheus_client) |

### Test Scenarios

#### 1. `test_successful_request_with_all_features`
Tests the complete workflow: cache miss → fetch → cache → cache hit
- Validates cache miss on first request
- Verifies response is cached with proper TTL
- Confirms cache hit on second request
- Validates metrics are recorded correctly

#### 2. `test_error_tracking_integration`
Tests error tracking with IAB VAST error codes and pixel firing
- Simulates various IAB VAST error codes (100, 300, 402)
- Verifies error pixels fired with macro substitution ([ERRORCODE], [TIMESTAMP])
- Tests concurrent error pixel firing
- Validates metrics recording for error events

#### 3. `test_wrapper_chain_with_metrics`
Tests wrapper chain resolution with depth and timing metrics
- Validates wrapper chain resolution tracking
- Measures chain depth
- Records resolution time
- Collects metrics for chain operations

#### 4. `test_cache_expiration_and_eviction`
Tests TTL expiration and LRU eviction mechanisms
- Validates entries expire after TTL
- Tests background cleanup task
- Verifies LRU eviction when max size reached
- Confirms cache statistics are updated correctly

#### 5. `test_concurrent_requests_with_caching`
Tests concurrent cache operations for race conditions
- 50 concurrent cache operations
- Validates thread-safety
- Verifies no race conditions
- Confirms statistics remain consistent

#### 6. `test_error_scenario_with_fallback`
Tests error handling: timeout → error tracking → fallback
- Simulates timeout error
- Tracks error with pixel firing
- Tests fallback mechanism
- Validates metrics for error scenarios

#### 7. `test_full_production_workflow`
Tests complete production workflow with all features integrated
- Cache layer integration
- Error tracking integration
- Metrics collection
- Complex workflow with errors and recovery
- Validates statistics across all components

#### 8. `test_edge_cases`
Tests edge cases: invalid inputs, empty URLs, disabled metrics
- Empty cache keys
- Empty error URL lists
- Metrics with `enabled=False`
- Cache with None/invalid values
- Graceful degradation

#### 9. `test_performance_benchmarks`
Performance testing: cache ops/sec, concurrent access
- Sequential cache operations benchmark
- Concurrent operations benchmark
- Performance assertions (>100 ops/sec for get/set)
- Load testing

#### 10. `test_cache_cleanup_task`
Tests background cleanup task for expired entries
- Validates cleanup task runs at intervals
- Verifies expired entries are removed
- Confirms non-expired entries remain

#### 11. `test_metrics_with_labels`
Tests metrics recording with various label combinations
- Different upstream labels
- Various error codes and types
- Creative selection strategies
- Label differentiation

#### 12. `test_error_tracker_context_manager`
Tests error tracker as async context manager
- Validates `__aenter__` initialization
- Validates `__aexit__` cleanup
- Tests HTTP client lifecycle management
- Both owned and provided client scenarios

## Running Tests

### Run all E2E tests:
```bash
pytest tests/e2e/ -v
```

### Run with coverage:
```bash
pytest tests/e2e/test_vast_production_features.py \
  --cov=xsp.protocols.vast.error_tracker \
  --cov=xsp.protocols.vast.cache \
  --cov=xsp.protocols.vast.metrics \
  --cov-report=term-missing
```

### Run specific test:
```bash
pytest tests/e2e/test_vast_production_features.py::test_full_production_workflow -v
```

### Run with performance output:
```bash
pytest tests/e2e/test_vast_production_features.py::test_performance_benchmarks -v -s
```

## Test Dependencies

- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `aiohttp` - HTTP client for error tracking
- `prometheus_client` (optional) - Metrics collection

## Notes

- Tests use `MemoryTransport` to avoid network dependencies
- Error tracking tests use mocked HTTP clients
- Metrics tests work with and without `prometheus_client` installed
- Performance benchmarks are environment-dependent
- Some warnings about unawaited coroutines are expected from mock internals

## IAB VAST 4.2 Compliance

These tests validate compliance with:
- IAB VAST 4.2 error codes (100-900 range)
- Error pixel macro substitution ([ERRORCODE], [TIMESTAMP])
- Wrapper chain resolution
- Error tracking and reporting

## Future Enhancements

- Add tests for wrapper chain with real VAST XML
- Add tests for creative selection strategies
- Add stress testing for cache under high load
- Add tests for metrics with real Prometheus integration
- Add tests for error recovery strategies
