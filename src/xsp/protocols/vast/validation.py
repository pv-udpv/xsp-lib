"""XML validation helpers for VAST."""

import xml.etree.ElementTree as ET
from typing import Any

from xsp.core.exceptions import ValidationError


class VastValidationError(ValidationError):
    """VAST XML validation failed."""


def validate_vast_xml(xml: str) -> dict[str, Any]:
    """
    Validate VAST XML structure.

    Args:
        xml: VAST XML string

    Returns:
        Basic parsed structure with version and ad count

    Raises:
        VastValidationError: If XML is invalid
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise VastValidationError(f"Invalid XML: {e}") from e

    if root.tag != "VAST" and root.tag != "VMAP":
        raise VastValidationError(f"Root element must be VAST or VMAP, got {root.tag}")

    version = root.get("version")
    if not version and root.tag == "VAST":
        raise VastValidationError("VAST version attribute missing")

    return {
        "version": version,
        "has_ads": len(root.findall(".//Ad")) > 0,
        "root_tag": root.tag,
    }
