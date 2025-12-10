"""Tests for orchestrator schemas."""


from xsp.orchestrator.schemas import AdRequest, AdResponse


def test_ad_request_required_fields():
    """Test AdRequest with required fields only."""
    request: AdRequest = AdRequest(
        slot_id="test-slot",
        user_id="user123",
    )

    assert request["slot_id"] == "test-slot"
    assert request["user_id"] == "user123"


def test_ad_request_all_fields():
    """Test AdRequest with all fields."""
    request: AdRequest = AdRequest(
        slot_id="pre-roll",
        user_id="user123",
        ip_address="192.168.1.1",
        device_type="mobile",
        content_url="https://example.com/video",
        content_duration=600.0,
        playhead_position=0.0,
        player_size=(1920, 1080),
        geo={"country": "US", "region": "CA"},
        extensions={"custom_field": "value"},
    )

    assert request["slot_id"] == "pre-roll"
    assert request["user_id"] == "user123"
    assert request["ip_address"] == "192.168.1.1"
    assert request["device_type"] == "mobile"
    assert request["content_url"] == "https://example.com/video"
    assert request["content_duration"] == 600.0
    assert request["playhead_position"] == 0.0
    assert request["player_size"] == (1920, 1080)
    assert request["geo"] == {"country": "US", "region": "CA"}
    assert request["extensions"] == {"custom_field": "value"}


def test_ad_response_success():
    """Test successful AdResponse."""
    response: AdResponse = AdResponse(
        success=True,
        slot_id="pre-roll",
        ad_id="ad-123",
        creative_url="https://cdn.example.com/video.mp4",
        creative_type="video/linear",
        format="mp4",
        duration=30.0,
        bitrate=2000,
        dimensions=(1920, 1080),
        tracking_urls={
            "impression": ["https://track.example.com/impression"],
            "complete": ["https://track.example.com/complete"],
        },
        ad_system="TestAdSystem",
        advertiser="TestAdvertiser",
        campaign_id="campaign-456",
        resolution_chain=["https://primary.example.com"],
        used_fallback=False,
        cached=False,
        resolution_time_ms=150.5,
    )

    assert response["success"] is True
    assert response["slot_id"] == "pre-roll"
    assert response["ad_id"] == "ad-123"
    assert response["creative_url"] == "https://cdn.example.com/video.mp4"
    assert response["duration"] == 30.0
    assert "impression" in response["tracking_urls"]  # type: ignore


def test_ad_response_error():
    """Test error AdResponse."""
    response: AdResponse = AdResponse(
        success=False,
        slot_id="pre-roll",
        error="No ads available",
        error_code="NO_ADS",
    )

    assert response["success"] is False
    assert response["slot_id"] == "pre-roll"
    assert response["error"] == "No ads available"
    assert response["error_code"] == "NO_ADS"


def test_ad_response_with_extensions():
    """Test AdResponse with protocol-specific extensions."""
    response: AdResponse = AdResponse(
        success=True,
        slot_id="banner-top",
        extensions={
            "bid_price": 2.50,
            "adm": "<html>...</html>",
            "custom_data": {"key": "value"},
        },
    )

    assert response["success"] is True
    assert response["extensions"]["bid_price"] == 2.50  # type: ignore
    assert response["extensions"]["adm"] == "<html>...</html>"  # type: ignore
