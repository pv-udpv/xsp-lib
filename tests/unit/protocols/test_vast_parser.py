"""Tests for version-aware VAST parser."""

import pytest

from xsp.protocols.vast.parser import VastParser, ElementDefinition
from xsp.protocols.vast.types import VastVersion


@pytest.fixture
def vast_42_xml():
    """Sample VAST 4.2 XML with version-specific elements."""
    return '''
<VAST version="4.2">
    <Ad id="123">
        <InLine>
            <AdSystem>TestSystem</AdSystem>
            <AdTitle>Test Ad</AdTitle>
            <Description>Test Description</Description>
            <Advertiser>Test Advertiser</Advertiser>
            <Impression>https://example.com/impression</Impression>
            <Error>https://example.com/error</Error>
            
            <!-- VAST 3.0+ elements -->
            <UniversalAdId idRegistry="Ad-ID">test-ad-id-123</UniversalAdId>
            <Pricing model="CPM" currency="USD">5.00</Pricing>
            
            <!-- VAST 4.0+ elements -->
            <Category authority="IAB">IAB1</Category>
            <Mezzanine delivery="progressive">
                <![CDATA[https://example.com/mezzanine.mp4]]>
            </Mezzanine>
            
            <!-- VAST 4.2+ elements -->
            <BlockedAdCategories>IAB25,IAB26</BlockedAdCategories>
        </InLine>
    </Ad>
</VAST>
'''.strip()


@pytest.fixture
def vast_30_xml():
    """Sample VAST 3.0 XML."""
    return '''
<VAST version="3.0">
    <Ad id="456">
        <InLine>
            <AdSystem>TestSystem30</AdSystem>
            <AdTitle>VAST 3.0 Ad</AdTitle>
            <Impression>https://example.com/impression</Impression>
            <UniversalAdId idRegistry="Ad-ID">vast3-ad-id</UniversalAdId>
        </InLine>
    </Ad>
</VAST>
'''.strip()


def test_parser_v42_parses_all_elements(vast_42_xml):
    """Test VAST 4.2 parser includes all version-compatible elements."""
    parser = VastParser(version=VastVersion.V4_2)
    result = parser.parse_vast(vast_42_xml)

    # Check core elements (2.0+)
    assert result["ad_system"] == "TestSystem"
    assert result["ad_title"] == "Test Ad"
    assert result["description"] == "Test Description"
    assert result["advertiser"] == "Test Advertiser"
    assert "https://example.com/impression" in result["impression"]

    # Check 3.0+ elements
    assert "universal_ad_id" in result
    assert "pricing" in result

    # Check 4.0+ elements
    assert "category" in result
    assert "mezzanine" in result

    # Check 4.2+ elements
    assert "blocked_ad_categories" in result


def test_parser_v30_filters_out_4x_elements(vast_42_xml):
    """Test VAST 3.0 parser excludes 4.x elements."""
    parser = VastParser(version=VastVersion.V3_0)
    result = parser.parse_vast(vast_42_xml)

    # Core elements should be present
    assert result["ad_system"] == "TestSystem"
    assert result["ad_title"] == "Test Ad"

    # 3.0 elements should be present
    assert "universal_ad_id" in result
    assert "pricing" in result

    # 4.0+ elements should NOT be present
    assert "category" not in result
    assert "mezzanine" not in result

    # 4.2+ elements should NOT be present
    assert "blocked_ad_categories" not in result


def test_parser_v30_parses_30_xml(vast_30_xml):
    """Test VAST 3.0 parser correctly parses 3.0 XML."""
    parser = VastParser(version=VastVersion.V3_0)
    result = parser.parse_vast(vast_30_xml)

    assert result["version"] == "3.0"
    assert result["ad_system"] == "TestSystem30"
    assert result["ad_title"] == "VAST 3.0 Ad"
    assert "universal_ad_id" in result


def test_strict_mode_raises_on_version_mismatch(vast_42_xml):
    """Test strict mode raises error on version mismatch."""
    parser = VastParser(version=VastVersion.V3_0, strict=True)

    with pytest.raises(ValueError, match="version mismatch"):
        parser.parse_vast(vast_42_xml)


def test_strict_mode_allows_matching_version(vast_42_xml):
    """Test strict mode allows matching version."""
    parser = VastParser(version=VastVersion.V4_2, strict=True)
    result = parser.parse_vast(vast_42_xml)

    assert result["version"] == "4.2"
    assert result["ad_system"] == "TestSystem"


def test_custom_element_registration():
    """Test custom element registration."""
    xml = '''
<VAST version="4.2">
    <Ad>
        <InLine>
            <AdSystem>Test</AdSystem>
            <CustomTracking url="https://example.com/track" type="custom"/>
        </InLine>
    </Ad>
</VAST>
'''.strip()

    parser = VastParser(version=VastVersion.V4_2)
    parser.register_element(
        name="custom_tracking",
        xpath=".//CustomTracking",
        introduced=VastVersion.V3_0,
        parser_func=lambda el: {
            "url": el.get("url"),
            "type": el.get("type"),
        },
    )

    result = parser.parse_vast(xml)

    assert "custom_tracking" in result
    assert result["custom_tracking"]["url"] == "https://example.com/track"
    assert result["custom_tracking"]["type"] == "custom"


def test_custom_element_filtered_by_version():
    """Test custom element filtered by introduced version."""
    xml = '''
<VAST version="3.0">
    <Ad>
        <InLine>
            <AdSystem>Test</AdSystem>
            <FutureElement>Value</FutureElement>
        </InLine>
    </Ad>
</VAST>
'''.strip()

    parser = VastParser(version=VastVersion.V3_0)
    parser.register_element(
        name="future_element",
        xpath=".//FutureElement",
        introduced=VastVersion.V4_2,  # Introduced in 4.2, not 3.0
    )

    result = parser.parse_vast(xml)

    # Element should NOT be parsed (introduced in future version)
    assert "future_element" not in result


def test_parser_version_metadata():
    """Test parser includes version metadata in result."""
    xml = '<VAST version="4.2"><Ad><InLine><AdSystem>Test</AdSystem></InLine></Ad></VAST>'

    parser = VastParser(version=VastVersion.V3_0)
    result = parser.parse_vast(xml)

    assert result["version"] == "4.2"  # From XML
    assert result["_parser_version"] == "3.0"  # Parser config


def test_element_compatibility_check():
    """Test element compatibility checking logic."""
    parser = VastParser(version=VastVersion.V4_0)

    # Element introduced in 3.0, compatible with 4.0
    elem_30 = ElementDefinition(
        xpath=".//Test",
        introduced=VastVersion.V3_0,
    )
    assert parser._is_element_compatible(elem_30) is True

    # Element introduced in 4.2, NOT compatible with 4.0
    elem_42 = ElementDefinition(
        xpath=".//Test",
        introduced=VastVersion.V4_2,
    )
    assert parser._is_element_compatible(elem_42) is False

    # Element introduced in 2.0, deprecated in 4.0, NOT compatible
    elem_deprecated = ElementDefinition(
        xpath=".//Test",
        introduced=VastVersion.V2_0,
        deprecated=VastVersion.V4_0,
    )
    assert parser._is_element_compatible(elem_deprecated) is False
