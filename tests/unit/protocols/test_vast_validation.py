"""Tests for VAST XML validation."""

import pytest

from xsp.protocols.vast.validation import VastValidationError, validate_vast_xml


def test_validate_vast_xml_valid() -> None:
    """Test validation with valid VAST XML."""
    xml = '<VAST version="4.2"><Ad id="123"></Ad></VAST>'
    result = validate_vast_xml(xml)

    assert result["version"] == "4.2"
    assert result["has_ads"] is True


def test_validate_vast_xml_invalid_root() -> None:
    """Test validation with invalid root element."""
    xml = '<Invalid version="4.2"></Invalid>'

    with pytest.raises(VastValidationError, match="Root element must be"):
        validate_vast_xml(xml)


def test_validate_vast_xml_missing_version() -> None:
    """Test validation with missing version."""
    xml = "<VAST><Ad id=\"123\"></Ad></VAST>"

    with pytest.raises(VastValidationError, match="version attribute missing"):
        validate_vast_xml(xml)


def test_validate_vast_xml_malformed() -> None:
    """Test validation with malformed XML."""
    xml = '<VAST version="4.2"><Ad>'

    with pytest.raises(VastValidationError, match="Invalid XML"):
        validate_vast_xml(xml)
