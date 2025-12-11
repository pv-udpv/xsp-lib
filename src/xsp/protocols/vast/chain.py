"""VAST wrapper chain resolution configuration.

Provides configuration classes for controlling VAST wrapper chain
resolution behavior including depth limits, fallback strategies,
and creative selection.

References:
    - VAST 4.2 §2.4.3.4: Wrapper element and chain resolution
    - VAST 4.2 §2.4.1.2: maxwrapperdepth attribute
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResolutionStrategy(str, Enum):
    """Strategy for resolving VAST wrapper chains.

    Determines how the resolver follows wrapper chains to find
    the final InLine creative.

    Per VAST 4.2 §2.4.3.4 - Wrappers must be resolved recursively
    to obtain the final InLine ad response.
    """

    RECURSIVE = "recursive"
    """Follow wrapper chain recursively until InLine is found."""

    FIRST_INLINE = "first_inline"
    """Return the first InLine response encountered."""

    MAX_DEPTH = "max_depth"
    """Continue until max_depth is reached."""

    PARALLEL = "parallel"
    """Resolve multiple wrapper chains in parallel (for ad pods)."""


class SelectionStrategy(str, Enum):
    """Strategy for selecting creative from resolved VAST response.

    Determines which creative/media file to select when multiple
    options are available in the final InLine response.

    Per VAST 4.2 §2.4.4.1 - MediaFile selection based on delivery,
    dimensions, bitrate, and codec compatibility.
    """

    HIGHEST_BITRATE = "highest_bitrate"
    """Select media file with highest bitrate."""

    LOWEST_BITRATE = "lowest_bitrate"
    """Select media file with lowest bitrate."""

    BEST_QUALITY = "best_quality"
    """Select based on resolution and codec quality."""

    CUSTOM = "custom"
    """Use custom selection function."""


@dataclass
class VastChainConfig:
    """Configuration for VAST wrapper chain resolution.

    Controls wrapper chain resolution behavior including depth limits,
    timeout settings, fallback handling, and creative selection.

    Per VAST 4.2 §2.4.1.2 - Wrapper elements support maxwrapperdepth
    attribute to prevent infinite recursion.

    Example:
        >>> config = VastChainConfig(
        ...     max_depth=5,
        ...     timeout=10.0,
        ...     enable_fallbacks=True,
        ...     resolution_strategy=ResolutionStrategy.RECURSIVE
        ... )
    """

    max_depth: int = 5
    """Maximum wrapper chain depth. Per VAST 4.2 default is 5."""

    timeout: float = 30.0
    """Total timeout for entire chain resolution in seconds."""

    per_request_timeout: float = 10.0
    """Timeout for each individual wrapper request in seconds."""

    enable_fallbacks: bool = True
    """Enable fallback to secondary upstreams on primary failure."""

    resolution_strategy: ResolutionStrategy = ResolutionStrategy.RECURSIVE
    """Strategy for resolving wrapper chains."""

    selection_strategy: SelectionStrategy = SelectionStrategy.HIGHEST_BITRATE
    """Strategy for selecting creative from resolved VAST."""

    follow_redirects: bool = True
    """Follow HTTP redirects in wrapper chain."""

    validate_each_response: bool = False
    """Validate XML structure of each wrapper response."""

    collect_tracking_urls: bool = True
    """Collect tracking URLs from all wrappers in chain."""

    collect_error_urls: bool = True
    """Collect error URLs from all wrappers in chain."""

    custom_selector: Any = None
    """Custom creative selector function when selection_strategy=CUSTOM."""

    additional_params: dict[str, Any] = field(default_factory=dict)
    """Additional parameters passed to upstream requests."""
