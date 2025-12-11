"""Tests for AdCOM validation functions."""

import pytest
from pydantic import ValidationError

from xsp.standards.adcom.context import App, Dooh, Site
from xsp.standards.adcom.enums import DeviceType
from xsp.standards.adcom.validation import (
    validate_ad,
    validate_context,
    validate_device,
    validate_placement,
    validate_regs,
    validate_user,
)


def test_validate_ad_success() -> None:
    """Test successful ad validation."""
    data = {
        "id": "ad-123",
        "adomain": ["advertiser.com"],
        "display": {"mime": "image/jpeg", "w": 300, "h": 250},
    }

    ad = validate_ad(data)

    assert ad.id == "ad-123"
    assert ad.display.w == 300


def test_validate_ad_with_video() -> None:
    """Test ad validation with video."""
    data = {
        "id": "ad-video-123",
        "video": {"mime": ["video/mp4"], "dur": 30},
    }

    ad = validate_ad(data)

    assert ad.id == "ad-video-123"
    assert ad.video.dur == 30


def test_validate_ad_failure_no_media() -> None:
    """Test ad validation fails without media subtype."""
    data = {"id": "ad-123"}

    with pytest.raises(ValidationError):
        validate_ad(data)


def test_validate_ad_failure_missing_id() -> None:
    """Test ad validation fails without required id."""
    data = {"display": {"mime": "image/jpeg"}}

    with pytest.raises(ValidationError):
        validate_ad(data)


def test_validate_placement_success() -> None:
    """Test successful placement validation."""
    data = {
        "tagid": "tag-123",
        "display": {"w": 300, "h": 250},
    }

    placement = validate_placement(data)

    assert placement.tagid == "tag-123"
    assert placement.display.w == 300


def test_validate_placement_with_video() -> None:
    """Test placement validation with video."""
    data = {
        "tagid": "tag-video-123",
        "video": {"mindur": 15, "maxdur": 30},
    }

    placement = validate_placement(data)

    assert placement.tagid == "tag-video-123"
    assert placement.video.mindur == 15


def test_validate_placement_failure_no_subtype() -> None:
    """Test placement validation fails without subtype."""
    data = {"tagid": "tag-123"}

    with pytest.raises(ValidationError):
        validate_placement(data)


def test_validate_context_site() -> None:
    """Test context validation for site."""
    data = {
        "id": "site-123",
        "domain": "example.com",
        "page": "https://example.com/page",
    }

    site = validate_context(data, context_type="site")

    assert isinstance(site, Site)
    assert site.id == "site-123"
    assert site.domain == "example.com"


def test_validate_context_app() -> None:
    """Test context validation for app."""
    data = {
        "id": "app-123",
        "bundle": "com.example.app",
        "name": "Example App",
    }

    app = validate_context(data, context_type="app")

    assert isinstance(app, App)
    assert app.id == "app-123"
    assert app.bundle == "com.example.app"


def test_validate_context_dooh() -> None:
    """Test context validation for dooh."""
    data = {
        "id": "dooh-123",
        "name": "Airport Display",
    }

    dooh = validate_context(data, context_type="dooh")

    assert isinstance(dooh, Dooh)
    assert dooh.id == "dooh-123"


def test_validate_context_invalid_type() -> None:
    """Test context validation with invalid type."""
    data = {"id": "test-123"}

    with pytest.raises(ValueError, match="Invalid context_type"):
        validate_context(data, context_type="invalid")


def test_validate_user_success() -> None:
    """Test successful user validation."""
    data = {
        "id": "user-123",
        "yob": 1990,
        "gender": "M",
    }

    user = validate_user(data)

    assert user.id == "user-123"
    assert user.yob == 1990
    assert user.gender == "M"


def test_validate_device_success() -> None:
    """Test successful device validation."""
    data = {
        "type": 4,  # PHONE
        "make": "Apple",
        "model": "iPhone",
        "os": "iOS",
    }

    device = validate_device(data)

    assert device.type == DeviceType.PHONE
    assert device.make == "Apple"
    assert device.model == "iPhone"


def test_validate_device_with_geo() -> None:
    """Test device validation with geo."""
    data = {
        "type": 4,
        "geo": {
            "type": 1,  # GPS_LOCATION
            "lat": 37.7749,
            "lon": -122.4194,
            "country": "USA",
        },
    }

    device = validate_device(data)

    assert device.geo.lat == 37.7749
    assert device.geo.country == "USA"


def test_validate_regs_success() -> None:
    """Test successful regs validation."""
    data = {
        "coppa": 1,
        "gdpr": 1,
    }

    regs = validate_regs(data)

    assert regs.coppa == 1
    assert regs.gdpr == 1


def test_validate_ad_accepts_unknown_fields() -> None:
    """Test that ad validation accepts unknown fields per spec."""
    data = {
        "id": "ad-123",
        "display": {"mime": "image/jpeg"},
        "unknown_field": "value",
        "another_unknown": 123,
    }

    ad = validate_ad(data)

    assert ad.id == "ad-123"
    # Unknown fields should be accepted in ext behavior


def test_validate_ad_with_ext() -> None:
    """Test ad validation with ext field."""
    data = {
        "id": "ad-123",
        "display": {"mime": "image/jpeg"},
        "ext": {"custom_vendor": "data", "another": 123},
    }

    ad = validate_ad(data)

    assert ad.ext["custom_vendor"] == "data"
    assert ad.ext["another"] == 123


def test_validate_placement_with_ext() -> None:
    """Test placement validation with ext field."""
    data = {
        "tagid": "tag-123",
        "display": {"w": 300, "h": 250},
        "ext": {"ssp_data": "value"},
    }

    placement = validate_placement(data)

    assert placement.ext["ssp_data"] == "value"


def test_validate_complex_ad() -> None:
    """Test validation of complex ad with multiple nested objects."""
    data = {
        "id": "ad-complex-123",
        "adomain": ["advertiser.com", "tracker.com"],
        "bundle": "com.example.app",
        "cat": ["IAB1", "IAB2"],
        "cattax": 2,
        "secure": 1,
        "display": {
            "mime": "image/jpeg",
            "w": 300,
            "h": 250,
            "banner": {
                "img": "https://cdn.example.com/banner.jpg",
                "link": "https://advertiser.com/landing",
            },
            "event": [
                {
                    "type": 1,  # IMPRESSION
                    "method": 1,  # IMAGE_PIXEL
                    "url": "https://tracker.com/impression",
                }
            ],
        },
        "audit": {
            "status": 3,  # APPROVED
            "feedback": ["Looks good"],
        },
    }

    ad = validate_ad(data)

    assert ad.id == "ad-complex-123"
    assert len(ad.adomain) == 2
    assert ad.display.banner.img == "https://cdn.example.com/banner.jpg"
    assert len(ad.display.event) == 1
    assert ad.audit.status == 3


def test_validate_complex_placement() -> None:
    """Test validation of complex placement with multiple nested objects."""
    data = {
        "tagid": "tag-complex-123",
        "secure": 1,
        "display": {
            "pos": 1,  # ABOVE_THE_FOLD
            "w": 300,
            "h": 250,
            "displayfmt": [{"w": 300, "h": 250}, {"w": 728, "h": 90}],
            "event": [
                {
                    "type": 1,  # IMPRESSION
                    "method": [1],  # IMAGE_PIXEL
                    "pxtrk": ["https://tracker.com/pixel"],
                }
            ],
        },
        "video": {
            "ptype": 1,  # IN_STREAM
            "mindur": 15,
            "maxdur": 30,
            "mime": ["video/mp4"],
        },
    }

    placement = validate_placement(data)

    assert placement.tagid == "tag-complex-123"
    assert placement.secure == 1
    assert len(placement.display.displayfmt) == 2
    assert placement.video.mindur == 15
