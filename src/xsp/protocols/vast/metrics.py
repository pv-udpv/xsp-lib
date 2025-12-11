"""VAST metrics integration with Prometheus compatibility."""

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

try:
    from prometheus_client import Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create dummy classes

    class Counter:
        def labels(self, **kwargs):
            return self

        def inc(self, amount=1):
            pass

    class Histogram:
        def labels(self, **kwargs):
            return self

        def observe(self, amount):
            pass

    class Gauge:
        def set(self, value):
            pass


@dataclass
class VastMetricLabels:
    """Labels for VAST metrics."""

    upstream: str = "unknown"
    version: str = "unknown"
    strategy: str = "unknown"
    error_code: str = "0"
    error_type: str = "none"


class VastMetrics:
    """Prometheus metrics for VAST operations."""

    def __init__(self, enabled: bool = True, namespace: str = "vast"):
        """Initialize metrics collector."""
        self.enabled = enabled and PROMETHEUS_AVAILABLE
        self.logger = logging.getLogger(__name__)

        if not self.enabled:
            if not PROMETHEUS_AVAILABLE:
                self.logger.warning("prometheus_client not available, metrics disabled")
            return

        # Request metrics
        self.requests_total = Counter(
            f"{namespace}_requests_total",
            "Total VAST requests",
            ["upstream", "version"],
        )

        self.request_duration = Histogram(
            f"{namespace}_request_duration_seconds",
            "VAST request duration",
            ["upstream", "version"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        self.response_size = Histogram(
            f"{namespace}_response_size_bytes",
            "VAST response size",
            ["upstream"],
            buckets=[1024, 10240, 102400, 1024000, 10240000],
        )

        # Error metrics
        self.errors_total = Counter(
            f"{namespace}_errors_total",
            "Total VAST errors",
            ["error_code", "error_type"],
        )

        self.error_pixels_fired = Counter(
            f"{namespace}_error_pixels_fired_total", "Total error pixels fired"
        )

        # Wrapper chain metrics
        self.chain_depth = Histogram(
            f"{namespace}_chain_depth",
            "VAST wrapper chain depth",
            buckets=[1, 2, 3, 4, 5, 10],
        )

        self.chain_resolution_duration = Histogram(
            f"{namespace}_chain_resolution_duration_seconds",
            "VAST chain resolution duration",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
        )

        # Cache metrics
        self.cache_hits = Counter(f"{namespace}_cache_hits_total", "Cache hits")

        self.cache_misses = Counter(f"{namespace}_cache_misses_total", "Cache misses")

        self.cache_size = Gauge(f"{namespace}_cache_size", "Current cache size")

        self.cache_evictions = Counter(f"{namespace}_cache_evictions_total", "Cache evictions")

        # Creative selection metrics
        self.creative_selections = Counter(
            f"{namespace}_creative_selections_total",
            "Creative selections",
            ["strategy"],
        )

        self.bitrate_distribution = Histogram(
            f"{namespace}_bitrate_kbps",
            "Selected creative bitrate",
            buckets=[100, 500, 1000, 2000, 5000, 10000],
        )

    def record_request(
        self,
        upstream: str,
        version: str,
        duration_seconds: float,
        response_size_bytes: int,
    ) -> None:
        """Record request metrics."""
        if not self.enabled:
            return

        self.requests_total.labels(upstream=upstream, version=version).inc()
        self.request_duration.labels(upstream=upstream, version=version).observe(duration_seconds)
        self.response_size.labels(upstream=upstream).observe(response_size_bytes)

    def record_error(self, error_code: int, error_type: str) -> None:
        """Record error metrics."""
        if not self.enabled:
            return

        self.errors_total.labels(error_code=str(error_code), error_type=error_type).inc()

    def record_error_pixel_fired(self, count: int = 1) -> None:
        """Record error pixel firing."""
        if not self.enabled:
            return

        self.error_pixels_fired.inc(count)

    def record_chain_resolution(self, depth: int, duration_seconds: float) -> None:
        """Record wrapper chain resolution."""
        if not self.enabled:
            return

        self.chain_depth.observe(depth)
        self.chain_resolution_duration.observe(duration_seconds)

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        if not self.enabled:
            return

        self.cache_hits.inc()

    def record_cache_miss(self) -> None:
        """Record cache miss."""
        if not self.enabled:
            return

        self.cache_misses.inc()

    def update_cache_size(self, size: int) -> None:
        """Update cache size gauge."""
        if not self.enabled:
            return

        self.cache_size.set(size)

    def record_cache_eviction(self, count: int = 1) -> None:
        """Record cache eviction."""
        if not self.enabled:
            return

        self.cache_evictions.inc(count)

    def record_creative_selection(self, strategy: str, bitrate_kbps: int | None = None) -> None:
        """Record creative selection."""
        if not self.enabled:
            return

        self.creative_selections.labels(strategy=strategy).inc()
        if bitrate_kbps is not None:
            self.bitrate_distribution.observe(bitrate_kbps)

    @asynccontextmanager
    async def track_request(self, upstream: str, version: str):
        """Context manager for tracking request duration."""
        start_time = time.time()
        try:
            yield
        finally:
            if self.enabled:
                duration = time.time() - start_time
                self.request_duration.labels(upstream=upstream, version=version).observe(duration)
