"""VAST Custom Creative Selection Example.

This example demonstrates how to implement custom creative selection
strategies for the VAST wrapper chain resolver.

Custom selectors enable sophisticated logic for choosing the best
creative based on device type, network conditions, codec support,
and business requirements.

Per VAST 4.2 §2.4.4.1 - MediaFile selection should consider delivery
method, dimensions, bitrate, codec, and scalability.
"""

import asyncio
import logging
from typing import Any

from xsp.protocols.vast import VastChainResolver, VastUpstream
from xsp.protocols.vast.chain import SelectionStrategy, VastChainConfig
from xsp.transports.http import HttpTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def mobile_optimized_selector(media_files: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select best creative for mobile devices.
    
    Selection priority:
    1. HLS streaming (adaptive bitrate) with .m3u8 extension
    2. MP4 progressive delivery
    3. Resolution <= 720p (HD-ready mobile)
    4. Lowest bitrate for bandwidth efficiency
    
    Args:
        media_files: List of MediaFile dictionaries from VAST response
    
    Returns:
        Selected MediaFile dict or None if no suitable file found
    
    Example MediaFile dict:
        {
            "delivery": "progressive",
            "type": "video/mp4",
            "width": 1280,
            "height": 720,
            "bitrate": 1500,
            "uri": "https://cdn.example.com/video.mp4"
        }
    """
    if not media_files:
        return None
    
    # Priority 1: HLS streaming for adaptive bitrate
    hls_files = [
        f for f in media_files
        if f.get("type") == "application/x-mpegURL"
        or (f.get("uri", "").endswith(".m3u8"))
    ]
    
    if hls_files:
        logger.info("  ✓ Selected HLS streaming for adaptive bitrate")
        return hls_files[0]
    
    # Priority 2: MP4 progressive delivery
    mp4_files = [
        f for f in media_files
        if f.get("type") == "video/mp4"
    ]
    
    if not mp4_files:
        # Fallback to any available file
        logger.warning("  ⚠ No MP4 files, using first available")
        return media_files[0]
    
    # Priority 3: Filter for mobile-friendly resolution (≤ 720p)
    mobile_resolution_files = [
        f for f in mp4_files
        if f.get("height", 0) <= 720
    ]
    
    if mobile_resolution_files:
        mp4_files = mobile_resolution_files
    else:
        logger.warning("  ⚠ No 720p or lower files, using higher resolution")
    
    # Priority 4: Select lowest bitrate for bandwidth efficiency
    files_with_bitrate = [f for f in mp4_files if f.get("bitrate")]
    
    if files_with_bitrate:
        selected = min(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
        logger.info(
            f"  ✓ Selected mobile-optimized MP4: "
            f"{selected.get('width')}x{selected.get('height')} @ {selected.get('bitrate')}kbps"
        )
        return selected
    
    # Fallback: first MP4 file
    logger.warning("  ⚠ No bitrate info, using first MP4")
    return mp4_files[0]


def desktop_quality_selector(media_files: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select best quality creative for desktop devices.
    
    Selection priority:
    1. 1080p or higher resolution
    2. Highest bitrate for quality
    3. H.264 codec preference (video/mp4)
    4. Progressive delivery for compatibility
    
    Args:
        media_files: List of MediaFile dictionaries
    
    Returns:
        Selected MediaFile dict or None
    """
    if not media_files:
        return None
    
    # Priority 1: Filter for 1080p or higher
    hd_files = [
        f for f in media_files
        if f.get("height", 0) >= 1080
    ]
    
    if hd_files:
        logger.info("  ✓ Found HD files (1080p+)")
        target_files = hd_files
    else:
        logger.warning("  ⚠ No 1080p+ files, using highest available")
        target_files = media_files
    
    # Priority 2: Select highest bitrate
    files_with_bitrate = [f for f in target_files if f.get("bitrate")]
    
    if files_with_bitrate:
        selected = max(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
        logger.info(
            f"  ✓ Selected high-quality desktop: "
            f"{selected.get('width')}x{selected.get('height')} @ {selected.get('bitrate')}kbps"
        )
        return selected
    
    # Fallback
    return target_files[0]


def codec_aware_selector(media_files: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select creative based on codec support and quality.
    
    Codec priority (modern browser):
    1. AV1 (best compression, modern browsers)
    2. VP9 (good compression, wide support)
    3. H.264/MPEG-4 (universal support)
    
    Then by quality:
    - Highest resolution
    - Highest bitrate
    
    Args:
        media_files: List of MediaFile dictionaries
    
    Returns:
        Selected MediaFile dict or None
    """
    if not media_files:
        return None
    
    # Check for AV1 codec
    av1_files = [
        f for f in media_files
        if "av1" in f.get("type", "").lower()
        or "av01" in f.get("uri", "").lower()
    ]
    
    if av1_files:
        logger.info("  ✓ AV1 codec available (best compression)")
        return max(av1_files, key=lambda f: (f.get("height", 0), f.get("bitrate", 0)))
    
    # Check for VP9 codec
    vp9_files = [
        f for f in media_files
        if f.get("type") == "video/webm"
        or "vp9" in f.get("type", "").lower()
    ]
    
    if vp9_files:
        logger.info("  ✓ VP9 codec available (good compression)")
        return max(vp9_files, key=lambda f: (f.get("height", 0), f.get("bitrate", 0)))
    
    # Fall back to H.264/MP4 (universal)
    mp4_files = [
        f for f in media_files
        if f.get("type") == "video/mp4"
    ]
    
    if mp4_files:
        logger.info("  ✓ H.264/MP4 codec (universal support)")
        return max(mp4_files, key=lambda f: (f.get("height", 0), f.get("bitrate", 0)))
    
    # Final fallback
    logger.warning("  ⚠ No preferred codec, using first available")
    return media_files[0]


def adaptive_network_selector(
    media_files: list[dict[str, Any]],
    estimated_bandwidth_kbps: int = 5000
) -> dict[str, Any] | None:
    """Select creative based on estimated network bandwidth.
    
    Selects appropriate quality level based on available bandwidth:
    - > 5000 kbps: HD quality (1080p+)
    - 2000-5000 kbps: SD quality (720p)
    - < 2000 kbps: Low quality (480p or lower)
    
    Args:
        media_files: List of MediaFile dictionaries
        estimated_bandwidth_kbps: Estimated network bandwidth in kbps
    
    Returns:
        Selected MediaFile dict or None
    """
    if not media_files:
        return None
    
    files_with_bitrate = [f for f in media_files if f.get("bitrate")]
    
    if not files_with_bitrate:
        logger.warning("  ⚠ No bitrate info, using first available")
        return media_files[0]
    
    # Filter files that fit within bandwidth (with 20% safety margin)
    max_bitrate = estimated_bandwidth_kbps * 0.8
    suitable_files = [
        f for f in files_with_bitrate
        if f.get("bitrate", 0) <= max_bitrate
    ]
    
    if suitable_files:
        # Select highest quality that fits
        selected = max(suitable_files, key=lambda f: f.get("bitrate", 0))
        logger.info(
            f"  ✓ Selected for {estimated_bandwidth_kbps}kbps bandwidth: "
            f"{selected.get('bitrate')}kbps @ "
            f"{selected.get('width')}x{selected.get('height')}"
        )
        return selected
    else:
        # Bandwidth too low, select lowest bitrate
        selected = min(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
        logger.warning(
            f"  ⚠ Limited bandwidth, using lowest quality: "
            f"{selected.get('bitrate')}kbps"
        )
        return selected


def business_logic_selector(
    media_files: list[dict[str, Any]],
    user_tier: str = "free"
) -> dict[str, Any] | None:
    """Select creative based on business logic (user subscription tier).
    
    Selection rules:
    - Premium users: Highest quality available (1080p+, highest bitrate)
    - Standard users: Medium quality (720p, medium bitrate)
    - Free users: Lower quality (480p or lower, lowest bitrate)
    
    Args:
        media_files: List of MediaFile dictionaries
        user_tier: User subscription tier ('free', 'standard', 'premium')
    
    Returns:
        Selected MediaFile dict or None
    """
    if not media_files:
        return None
    
    files_with_bitrate = [f for f in media_files if f.get("bitrate")]
    
    if not files_with_bitrate:
        return media_files[0]
    
    if user_tier == "premium":
        # Premium: Best quality available
        hd_files = [f for f in files_with_bitrate if f.get("height", 0) >= 1080]
        if hd_files:
            selected = max(hd_files, key=lambda f: f.get("bitrate", 0))
            logger.info(
                f"  ✓ Premium tier: HD quality "
                f"{selected.get('width')}x{selected.get('height')} @ "
                f"{selected.get('bitrate')}kbps"
            )
            return selected
        else:
            # No HD, use highest available
            selected = max(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
            logger.warning("  ⚠ Premium tier: No HD available, using best quality")
            return selected
    
    elif user_tier == "standard":
        # Standard: 720p medium quality
        sd_files = [
            f for f in files_with_bitrate
            if 480 <= f.get("height", 0) <= 720
        ]
        if sd_files:
            # Select middle bitrate
            sorted_files = sorted(sd_files, key=lambda f: f.get("bitrate", 0))
            selected = sorted_files[len(sorted_files) // 2]
            logger.info(
                f"  ✓ Standard tier: SD quality "
                f"{selected.get('width')}x{selected.get('height')} @ "
                f"{selected.get('bitrate')}kbps"
            )
            return selected
        else:
            # Fallback to median quality
            sorted_files = sorted(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
            return sorted_files[len(sorted_files) // 2]
    
    else:  # free tier
        # Free: Lowest quality
        selected = min(files_with_bitrate, key=lambda f: f.get("bitrate", 0))
        logger.info(
            f"  ✓ Free tier: Low quality "
            f"{selected.get('width')}x{selected.get('height')} @ "
            f"{selected.get('bitrate')}kbps"
        )
        return selected


async def demonstrate_custom_selectors():
    """Demonstrate different custom selection strategies."""
    logger.info("=== VAST Custom Creative Selection Examples ===\n")
    
    transport = HttpTransport()
    
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
        version="4.2"
    )
    
    upstreams = {"primary": upstream}
    
    # Example 1: Mobile-optimized selector
    logger.info("Example 1: Mobile-Optimized Selection")
    logger.info("-" * 60)
    
    config = VastChainConfig(selection_strategy=SelectionStrategy.CUSTOM)
    resolver = VastChainResolver(config=config, upstreams=upstreams)
    resolver.set_custom_selector(mobile_optimized_selector)
    
    try:
        result = await resolver.resolve(params={"w": "640", "h": "480"})
        if result.success and result.selected_creative:
            media = result.selected_creative["selected_media_file"]
            logger.info(f"  Final selection: {media['uri']}\n")
    except Exception as e:
        logger.error(f"  Error: {e}\n")
    
    # Example 2: Desktop quality selector
    logger.info("Example 2: Desktop Quality Selection")
    logger.info("-" * 60)
    
    resolver.set_custom_selector(desktop_quality_selector)
    
    try:
        result = await resolver.resolve(params={"w": "1920", "h": "1080"})
        if result.success and result.selected_creative:
            media = result.selected_creative["selected_media_file"]
            logger.info(f"  Final selection: {media['uri']}\n")
    except Exception as e:
        logger.error(f"  Error: {e}\n")
    
    # Example 3: Codec-aware selector
    logger.info("Example 3: Codec-Aware Selection")
    logger.info("-" * 60)
    
    resolver.set_custom_selector(codec_aware_selector)
    
    try:
        result = await resolver.resolve()
        if result.success and result.selected_creative:
            media = result.selected_creative["selected_media_file"]
            logger.info(f"  Final selection: {media['uri']}\n")
    except Exception as e:
        logger.error(f"  Error: {e}\n")
    
    # Example 4: Adaptive network selector
    logger.info("Example 4: Adaptive Network Selection")
    logger.info("-" * 60)
    
    # Simulate different network conditions
    network_conditions = [
        (10000, "Fast WiFi"),
        (3000, "4G Mobile"),
        (1000, "3G Mobile")
    ]
    
    for bandwidth, condition in network_conditions:
        logger.info(f"  Network condition: {condition} ({bandwidth}kbps)")
        
        # Create selector with network context
        def network_selector(files):
            return adaptive_network_selector(files, bandwidth)
        
        resolver.set_custom_selector(network_selector)
        
        try:
            result = await resolver.resolve()
            if result.success and result.selected_creative:
                media = result.selected_creative["selected_media_file"]
                logger.info(f"    Selected: {media.get('bitrate')}kbps\n")
        except Exception as e:
            logger.error(f"    Error: {e}\n")
    
    # Example 5: Business logic selector
    logger.info("Example 5: Business Logic Selection (User Tiers)")
    logger.info("-" * 60)
    
    user_tiers = ["premium", "standard", "free"]
    
    for tier in user_tiers:
        logger.info(f"  User tier: {tier}")
        
        # Create selector with user context
        def tier_selector(files):
            return business_logic_selector(files, tier)
        
        resolver.set_custom_selector(tier_selector)
        
        try:
            result = await resolver.resolve()
            if result.success and result.selected_creative:
                media = result.selected_creative["selected_media_file"]
                logger.info(f"    Selected: {media.get('bitrate')}kbps\n")
        except Exception as e:
            logger.error(f"    Error: {e}\n")
    
    await transport.close()
    
    logger.info("=" * 60)
    logger.info("All custom selector examples completed!")


async def main():
    """Run custom selector examples."""
    logger.warning("Note: Examples use placeholder URLs (example.com)")
    logger.warning("Replace with actual VAST endpoints for real usage.\n")
    
    try:
        await demonstrate_custom_selectors()
    except KeyboardInterrupt:
        logger.info("\nExamples interrupted by user")
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
