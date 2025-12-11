"""VAST error tracking per IAB VAST 4.2 specification."""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import IntEnum

import aiohttp


class VastErrorCode(IntEnum):
    """IAB VAST 4.2 error codes."""

    # XML parsing errors (100-199)
    XML_PARSING_ERROR = 100
    VAST_SCHEMA_VALIDATION_ERROR = 101
    VAST_VERSION_NOT_SUPPORTED = 102

    # Trafficking errors (200-299)
    TRAFFICKING_ERROR = 200
    VIDEO_PLAYER_EXPECTING_DIFFERENT_LINEARITY = 201
    VIDEO_PLAYER_EXPECTING_DIFFERENT_DURATION = 202
    VIDEO_PLAYER_EXPECTING_DIFFERENT_SIZE = 203

    # Wrapper errors (300-399)
    WRAPPER_LIMIT_REACHED = 300
    NO_VAST_RESPONSE_AFTER_WRAPPER = 301
    WRAPPER_TIMEOUT = 302

    # Video/media errors (400-499)
    GENERAL_LINEAR_ERROR = 400
    FILE_NOT_FOUND = 401
    TIMEOUT = 402
    MEDIA_FILE_DISPLAY_ERROR = 403

    # VPAID errors (500-599)
    GENERAL_VPAID_ERROR = 500

    # Verification errors (600-699)
    GENERAL_VERIFICATION_ERROR = 600

    # Undefined error
    UNDEFINED_ERROR = 900


@dataclass
class VastErrorTrackerConfig:
    """Configuration for VAST error tracker."""

    max_concurrent_fires: int = 10
    fire_timeout_seconds: float = 5.0
    enable_logging: bool = True


class VastErrorTracker:
    """Tracks and fires VAST error pixels per IAB VAST 4.2 spec."""

    def __init__(
        self,
        config: VastErrorTrackerConfig | None = None,
        http_client: aiohttp.ClientSession | None = None,
    ):
        """Initialize error tracker with optional HTTP client."""
        self.config = config or VastErrorTrackerConfig()
        self._http_client = http_client
        self._owns_client = http_client is None
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_fires)
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self) -> "VastErrorTracker":
        if self._owns_client:
            self._http_client = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self._owns_client and self._http_client:
            await self._http_client.close()

    async def track_error(
        self,
        error_code: VastErrorCode,
        error_urls: list[str],
        additional_context: dict | None = None,
    ) -> None:
        """Track error and fire error pixels in parallel."""
        if self.config.enable_logging:
            self.logger.error(
                "VAST error occurred",
                extra={
                    "error_code": error_code.value,
                    "error_name": error_code.name,
                    "num_urls": len(error_urls),
                    "context": additional_context or {},
                },
            )

        # Fire error pixels in parallel
        tasks = [self._fire_error_pixel(url, error_code) for url in error_urls]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _fire_error_pixel(self, url: str, error_code: VastErrorCode) -> None:
        """Fire a single error pixel with macro substitution."""
        async with self._semaphore:
            try:
                # Substitute macros
                substituted_url = url.replace("[ERRORCODE]", str(error_code.value))
                substituted_url = substituted_url.replace(
                    "[TIMESTAMP]", str(int(time.time() * 1000))
                )

                if not self._http_client:
                    return

                async with self._http_client.get(
                    substituted_url,
                    timeout=aiohttp.ClientTimeout(total=self.config.fire_timeout_seconds),
                ) as response:
                    if self.config.enable_logging and response.status >= 400:
                        self.logger.warning(
                            f"Error pixel fire failed with status {response.status}",
                            extra={"url": substituted_url, "error_code": error_code.value},
                        )
            except Exception as e:
                if self.config.enable_logging:
                    self.logger.warning(
                        f"Failed to fire error pixel: {e}",
                        extra={"url": url, "error_code": error_code.value},
                    )
