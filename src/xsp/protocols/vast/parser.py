"""Version-aware VAST XML parser."""

from dataclasses import dataclass
from typing import Any, Callable
from xml.etree import ElementTree as ET

from .types import VastVersion


@dataclass
class ElementDefinition:
    """VAST XML element definition with version info."""

    xpath: str
    introduced: VastVersion
    deprecated: VastVersion | None = None
    required: bool = False
    parser_func: Callable[[ET.Element], Any] | None = None


class VastParser:
    """
    Version-aware VAST XML parser.

    Parses VAST XML with automatic filtering of version-incompatible elements.
    Supports VAST 2.0, 3.0, 4.0, 4.1, 4.2 with version-specific features.
    """

    # Element registry organized by version
    ELEMENT_REGISTRY: dict[str, ElementDefinition] = {
        # Core elements (VAST 2.0+)
        "ad_system": ElementDefinition(
            xpath=".//AdSystem",
            introduced=VastVersion.V2_0,
            required=True,
        ),
        "ad_title": ElementDefinition(
            xpath=".//AdTitle",
            introduced=VastVersion.V2_0,
        ),
        "description": ElementDefinition(
            xpath=".//Description",
            introduced=VastVersion.V2_0,
        ),
        "advertiser": ElementDefinition(
            xpath=".//Advertiser",
            introduced=VastVersion.V2_0,
        ),
        "survey": ElementDefinition(
            xpath=".//Survey",
            introduced=VastVersion.V2_0,
        ),
        "error": ElementDefinition(
            xpath=".//Error",
            introduced=VastVersion.V2_0,
        ),
        "impression": ElementDefinition(
            xpath=".//Impression",
            introduced=VastVersion.V2_0,
        ),
        # VAST 3.0+ elements
        "universal_ad_id": ElementDefinition(
            xpath=".//UniversalAdId",
            introduced=VastVersion.V3_0,
        ),
        "ad_verifications": ElementDefinition(
            xpath=".//AdVerifications",
            introduced=VastVersion.V3_0,
        ),
        "pricing": ElementDefinition(
            xpath=".//Pricing",
            introduced=VastVersion.V3_0,
        ),
        # VAST 4.0+ elements
        "mezzanine": ElementDefinition(
            xpath=".//Mezzanine",
            introduced=VastVersion.V4_0,
        ),
        "category": ElementDefinition(
            xpath=".//Category",
            introduced=VastVersion.V4_0,
        ),
        # VAST 4.1+ elements
        "ad_choices": ElementDefinition(
            xpath=".//AdChoices",
            introduced=VastVersion.V4_1,
        ),
        # VAST 4.2+ elements
        "blocked_ad_categories": ElementDefinition(
            xpath=".//BlockedAdCategories",
            introduced=VastVersion.V4_2,
        ),
    }

    def __init__(
        self,
        version: VastVersion = VastVersion.V4_2,
        strict: bool = False,
    ):
        """
        Initialize version-aware parser.

        Args:
            version: VAST version to parse as
            strict: If True, raise errors on version mismatch
        """
        self.version = version
        self.strict = strict
        self.custom_elements: dict[str, ElementDefinition] = {}

    def parse_vast(self, xml: str) -> dict[str, Any]:
        """
        Parse VAST XML with version awareness.

        Args:
            xml: VAST XML string

        Returns:
            Parsed VAST data with only version-compatible elements

        Raises:
            ValueError: If strict=True and version mismatch
            ET.ParseError: If XML is malformed
        """
        root = ET.fromstring(xml)

        # Detect version from XML
        detected_version = root.get("version")
        if detected_version and self.strict:
            # In strict mode, verify version matches
            if detected_version != self.version.value:
                raise ValueError(
                    f"VAST version mismatch: expected {self.version.value}, "
                    f"got {detected_version}"
                )

        result: dict[str, Any] = {
            "version": detected_version or "unknown",
            "_parser_version": self.version.value,
        }

        # Parse only version-compatible elements
        combined_registry = {**self.ELEMENT_REGISTRY, **self.custom_elements}

        for element_name, element_def in combined_registry.items():
            if not self._is_element_compatible(element_def):
                continue

            elements = root.findall(element_def.xpath)
            if elements:
                if element_def.parser_func:
                    # Custom parser function
                    if len(elements) == 1:
                        result[element_name] = element_def.parser_func(elements[0])
                    else:
                        result[element_name] = [
                            element_def.parser_func(el) for el in elements
                        ]
                else:
                    # Default text extraction
                    if len(elements) == 1:
                        result[element_name] = elements[0].text
                    else:
                        result[element_name] = [el.text for el in elements]

        return result

    def register_element(
        self,
        name: str,
        xpath: str,
        introduced: VastVersion,
        deprecated: VastVersion | None = None,
        parser_func: Callable[[ET.Element], Any] | None = None,
    ) -> None:
        """
        Register custom element for parsing.

        Useful for provider-specific extensions.

        Args:
            name: Element name (key in result dict)
            xpath: XPath to find element
            introduced: VAST version when element was introduced
            deprecated: Optional version when element was deprecated
            parser_func: Optional custom parser function

        Example:
            parser.register_element(
                name="custom_tracking",
                xpath=".//CustomTracking",
                introduced=VastVersion.V3_0,
                parser_func=lambda el: {
                    "url": el.get("url"),
                    "type": el.get("type"),
                },
            )
        """
        self.custom_elements[name] = ElementDefinition(
            xpath=xpath,
            introduced=introduced,
            deprecated=deprecated,
            parser_func=parser_func,
        )

    def _is_element_compatible(self, element_def: ElementDefinition) -> bool:
        """
        Check if element is compatible with parser version.

        Args:
            element_def: Element definition

        Returns:
            True if element can be parsed with current version
        """
        version_order = [
            VastVersion.V2_0,
            VastVersion.V3_0,
            VastVersion.V4_0,
            VastVersion.V4_1,
            VastVersion.V4_2,
        ]

        current_idx = version_order.index(self.version)
        intro_idx = version_order.index(element_def.introduced)

        if intro_idx > current_idx:
            return False  # Element not yet introduced

        if element_def.deprecated:
            deprec_idx = version_order.index(element_def.deprecated)
            if deprec_idx <= current_idx:
                return False  # Element deprecated

        return True
