"""VAST Wrapper Chain Resolution Example.

This example demonstrates how to use the VAST wrapper chain resolver
to resolve wrapper chains with fallback support, creative selection,
and tracking integration.

Features demonstrated:
- Loading configuration from YAML
- Resolving wrapper chains
- Handling selection strategies
- Tracking impressions and errors
- Error handling and fallback behavior

Per VAST 4.2 §2.4.3.4 - Wrappers must be resolved recursively to obtain
the final InLine ad response.
"""

import asyncio
import logging
import os
from pathlib import Path

from xsp.protocols.vast import VastChainResolver, VastUpstream
from xsp.protocols.vast.chain import SelectionStrategy, VastChainConfig
from xsp.protocols.vast.config_loader import VastChainConfigLoader
from xsp.core.exceptions import UpstreamError, UpstreamTimeout
from xsp.transports.http import HttpTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def basic_chain_resolution():
    """Example 1: Basic wrapper chain resolution."""
    logger.info("=== Example 1: Basic Chain Resolution ===")
    
    transport = HttpTransport()
    
    # Create upstream
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
        version="4.2",
        enable_macros=True
    )
    
    # Configure resolver with defaults
    config = VastChainConfig()
    resolver = VastChainResolver(
        config=config,
        upstreams={"primary": upstream}
    )
    
    try:
        # Resolve wrapper chain
        result = await resolver.resolve(params={
            "w": "640",
            "h": "480",
            "playerVersion": "1.0"
        })
        
        if result.success:
            logger.info("✓ Resolution successful")
            logger.info(f"  Chain depth: {len(result.chain)}")
            logger.info(f"  Resolution time: {result.resolution_time_ms:.2f}ms")
            
            # Display chain
            for i, url in enumerate(result.chain, 1):
                logger.info(f"  [{i}] {url}")
            
            # Display selected creative
            if result.selected_creative:
                creative = result.selected_creative
                media = creative["selected_media_file"]
                
                logger.info(f"  Ad Title: {creative.get('ad_title')}")
                logger.info(f"  Ad System: {creative.get('ad_system')}")
                logger.info(f"  Media URL: {media['uri']}")
                logger.info(f"  Bitrate: {media.get('bitrate')}kbps")
                logger.info(f"  Resolution: {media.get('width')}x{media.get('height')}")
        else:
            logger.error(f"✗ Resolution failed: {result.error}")
    
    except UpstreamTimeout as e:
        logger.error(f"✗ Timeout: {e}")
    except UpstreamError as e:
        logger.error(f"✗ Upstream error: {e}")
    finally:
        await transport.close()


async def fallback_resolution():
    """Example 2: Resolution with multiple fallback upstreams."""
    logger.info("\n=== Example 2: Fallback Resolution ===")
    
    transport = HttpTransport()
    
    # Create multiple upstreams
    upstreams = {
        "primary": VastUpstream(
            transport=transport,
            endpoint="https://primary.ad-server.com/vast",
            version="4.2",
            enable_macros=True
        ),
        "secondary": VastUpstream(
            transport=transport,
            endpoint="https://secondary.ad-server.com/vast",
            version="4.2",
            enable_macros=True
        ),
        "tertiary": VastUpstream(
            transport=transport,
            endpoint="https://tertiary.ad-server.com/vast",
            version="4.2",
            enable_macros=True
        )
    }
    
    # Configure with fallbacks enabled
    config = VastChainConfig(
        max_depth=5,
        timeout=30.0,
        enable_fallbacks=True,
        selection_strategy=SelectionStrategy.HIGHEST_BITRATE
    )
    
    resolver = VastChainResolver(config=config, upstreams=upstreams)
    
    try:
        result = await resolver.resolve()
        
        if result.success:
            logger.info("✓ Resolution successful")
            logger.info(f"  Used fallback: {result.used_fallback}")
            logger.info(f"  Chain depth: {len(result.chain)}")
            logger.info(f"  Resolution time: {result.resolution_time_ms:.2f}ms")
            
            if result.used_fallback:
                logger.warning("  Primary upstream failed, used fallback")
        else:
            logger.error(f"✗ All upstreams failed: {result.error}")
    
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
    finally:
        await transport.close()


async def selection_strategies():
    """Example 3: Different creative selection strategies."""
    logger.info("\n=== Example 3: Selection Strategies ===")
    
    transport = HttpTransport()
    
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
        version="4.2"
    )
    
    upstreams = {"primary": upstream}
    
    # Test different strategies
    strategies = [
        (SelectionStrategy.HIGHEST_BITRATE, "Highest Bitrate (Desktop)"),
        (SelectionStrategy.LOWEST_BITRATE, "Lowest Bitrate (Mobile)"),
        (SelectionStrategy.BEST_QUALITY, "Best Quality (Adaptive)")
    ]
    
    for strategy, description in strategies:
        logger.info(f"\n  Testing strategy: {description}")
        
        config = VastChainConfig(selection_strategy=strategy)
        resolver = VastChainResolver(config=config, upstreams=upstreams)
        
        try:
            result = await resolver.resolve()
            
            if result.success and result.selected_creative:
                media = result.selected_creative["selected_media_file"]
                logger.info(f"    Selected: {media['uri']}")
                logger.info(f"    Bitrate: {media.get('bitrate')}kbps")
                logger.info(f"    Size: {media.get('width')}x{media.get('height')}")
        
        except Exception as e:
            logger.error(f"    Error: {e}")
    
    await transport.close()


async def tracking_integration():
    """Example 4: Impression and error tracking integration."""
    logger.info("\n=== Example 4: Tracking Integration ===")
    
    transport = HttpTransport()
    
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
        version="4.2"
    )
    
    # Enable tracking collection
    config = VastChainConfig(
        collect_tracking_urls=True,
        collect_error_urls=True
    )
    
    resolver = VastChainResolver(
        config=config,
        upstreams={"primary": upstream}
    )
    
    try:
        result = await resolver.resolve()
        
        if result.success and result.vast_data:
            # Get tracking URLs
            impressions = result.vast_data.get("impressions", [])
            error_urls = result.vast_data.get("error_urls", [])
            tracking_events = result.vast_data.get("tracking_events", {})
            
            logger.info("✓ Resolution successful")
            logger.info(f"  Impression URLs: {len(impressions)}")
            logger.info(f"  Error URLs: {len(error_urls)}")
            logger.info(f"  Tracking events: {len(tracking_events)}")
            
            # Display impression URLs
            if impressions:
                logger.info("\n  Impression URLs:")
                for i, url in enumerate(impressions[:3], 1):  # Show first 3
                    logger.info(f"    [{i}] {url}")
                if len(impressions) > 3:
                    logger.info(f"    ... and {len(impressions) - 3} more")
            
            # Display tracking events
            if tracking_events:
                logger.info("\n  Tracking Events:")
                for event_type, urls in tracking_events.items():
                    logger.info(f"    {event_type}: {len(urls)} URL(s)")
            
            # Example: Fire impression tracking when ad displays
            logger.info("\n  Firing impression tracking pixels...")
            for url in impressions[:2]:  # Fire first 2 as example
                asyncio.create_task(fire_tracking_pixel(url))
        
        else:
            logger.error(f"✗ Resolution failed: {result.error}")
            
            # Fire error tracking
            if result.vast_data:
                error_urls = result.vast_data.get("error_urls", [])
                if error_urls:
                    logger.info("  Firing error tracking pixels...")
                    await resolver._track_error(error_urls, error_code="303")
    
    except Exception as e:
        logger.error(f"✗ Error: {e}")
    finally:
        await transport.close()


async def yaml_configuration():
    """Example 5: Load configuration from YAML file."""
    logger.info("\n=== Example 5: YAML Configuration ===")
    
    # Set environment variables (would normally be set in deployment)
    os.environ["PRIMARY_VAST_ENDPOINT"] = "https://primary.example.com/vast"
    os.environ["SECONDARY_VAST_ENDPOINT"] = "https://secondary.example.com/vast"
    
    # Path to YAML config
    config_path = Path(__file__).parent.parent / "tests" / "fixtures" / "vast_chains.yaml"
    
    if not config_path.exists():
        logger.warning(f"  Config file not found: {config_path}")
        logger.info("  Skipping YAML configuration example")
        return
    
    transport = HttpTransport()
    
    try:
        # Load all resolvers from YAML
        resolvers = VastChainConfigLoader.load(config_path, transport)
        
        logger.info(f"✓ Loaded {len(resolvers)} chain configurations")
        logger.info(f"  Available chains: {list(resolvers.keys())}")
        
        # Use default chain
        if "default" in resolvers:
            resolver = resolvers["default"]
            result = await resolver.resolve(params={"w": "1920", "h": "1080"})
            
            if result.success:
                logger.info("\n  Default chain resolution:")
                logger.info(f"    Chain depth: {len(result.chain)}")
                logger.info(f"    Resolution time: {result.resolution_time_ms:.2f}ms")
        
        # Use mobile chain (if available)
        if "low_bandwidth" in resolvers:
            resolver = resolvers["low_bandwidth"]
            result = await resolver.resolve(params={"w": "640", "h": "480"})
            
            if result.success:
                logger.info("\n  Low bandwidth chain resolution:")
                logger.info(f"    Chain depth: {len(result.chain)}")
                logger.info(f"    Resolution time: {result.resolution_time_ms:.2f}ms")
    
    except FileNotFoundError as e:
        logger.error(f"✗ Config file not found: {e}")
    except ValueError as e:
        logger.error(f"✗ Invalid configuration: {e}")
    except Exception as e:
        logger.error(f"✗ Error: {e}")
    finally:
        await transport.close()


async def fire_tracking_pixel(url: str) -> None:
    """Fire tracking pixel (fire-and-forget).
    
    Sends HTTP GET request to tracking URL without blocking.
    Errors are logged but don't propagate.
    
    Per VAST 4.2 - Tracking pixels should not block ad playback.
    
    Args:
        url: Tracking URL to fire
    """
    try:
        # Create temporary transport for pixel
        transport = HttpTransport()
        
        # Send GET request with short timeout
        await asyncio.wait_for(
            transport.send(endpoint=url, payload=None, metadata=None, timeout=5.0),
            timeout=5.0
        )
        
        logger.debug(f"    Fired tracking pixel: {url}")
        
        await transport.close()
    
    except asyncio.TimeoutError:
        logger.warning(f"    Timeout firing pixel: {url}")
    except Exception as e:
        logger.warning(f"    Error firing pixel {url}: {e}")


async def error_handling_example():
    """Example 6: Comprehensive error handling."""
    logger.info("\n=== Example 6: Error Handling ===")
    
    transport = HttpTransport()
    
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://invalid.example.com/vast",  # Invalid endpoint
        version="4.2"
    )
    
    config = VastChainConfig(
        max_depth=3,
        timeout=10.0,
        enable_fallbacks=False  # No fallbacks for this example
    )
    
    resolver = VastChainResolver(
        config=config,
        upstreams={"primary": upstream}
    )
    
    try:
        result = await resolver.resolve()
        
        if not result.success:
            logger.error(f"✗ Resolution failed: {result.error}")
            logger.info(f"  Resolution time: {result.resolution_time_ms:.2f}ms")
            logger.info(f"  Used fallback: {result.used_fallback}")
            
            # Determine error type
            error_msg = str(result.error)
            
            if "timeout" in error_msg.lower():
                logger.info("  Error type: Timeout")
                logger.info("  Action: Increase timeout or reduce max_depth")
            
            elif "max wrapper depth" in error_msg.lower():
                logger.info("  Error type: Depth limit exceeded")
                logger.info("  Action: Check for circular wrapper references")
            
            elif "missing VASTAdTagURI" in error_msg.lower():
                logger.info("  Error type: Invalid VAST XML")
                logger.info("  Action: Validate upstream VAST responses")
            
            else:
                logger.info("  Error type: Generic upstream error")
                logger.info("  Action: Check network connectivity and upstream health")
            
            # In production: serve default ad
            logger.info("\n  Production fallback: Serving default ad")
    
    except UpstreamTimeout as e:
        logger.error(f"✗ Timeout exception: {e}")
        logger.info("  Production fallback: Serving default ad")
    
    except UpstreamError as e:
        logger.error(f"✗ Upstream exception: {e}")
        logger.info("  Production fallback: Serving default ad")
    
    except Exception as e:
        logger.error(f"✗ Unexpected exception: {e}")
        logger.info("  Production fallback: Serving default ad")
    
    finally:
        await transport.close()


async def main():
    """Run all examples."""
    logger.info("VAST Wrapper Chain Resolution Examples")
    logger.info("=" * 60)
    
    # Note: These examples use example.com URLs which won't work in practice.
    # In real usage, replace with actual VAST ad server endpoints.
    
    logger.warning("\nNote: Examples use placeholder URLs (example.com)")
    logger.warning("Replace with actual VAST endpoints for real usage.\n")
    
    try:
        # Run examples (comment out as needed)
        await basic_chain_resolution()
        await fallback_resolution()
        await selection_strategies()
        await tracking_integration()
        await yaml_configuration()
        await error_handling_example()
        
        logger.info("\n" + "=" * 60)
        logger.info("All examples completed!")
    
    except KeyboardInterrupt:
        logger.info("\nExamples interrupted by user")
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
