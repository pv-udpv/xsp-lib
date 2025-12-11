"""Tests for OpenRTB data models."""

import json

from xsp.protocols.openrtb.models import (
    App,
    Bid,
    BidRequest,
    BidResponse,
    Device,
    Imp,
    SeatBid,
    Site,
    User,
)


class TestUser:
    """Tests for User model."""

    def test_user_creation(self) -> None:
        """Test creating User object."""
        user: User = {
            "id": "user123",
            "buyeruid": "buyer456",
        }
        assert user["id"] == "user123"
        assert user["buyeruid"] == "buyer456"

    def test_user_optional_fields(self) -> None:
        """Test User with only required fields."""
        user: User = {"id": "user123"}
        assert user["id"] == "user123"
        assert "buyeruid" not in user

    def test_user_json_serialization(self) -> None:
        """Test User JSON serialization."""
        user: User = {"id": "user123", "buyeruid": "buyer456"}
        json_str = json.dumps(user)
        deserialized = json.loads(json_str)
        assert deserialized["id"] == "user123"
        assert deserialized["buyeruid"] == "buyer456"


class TestDevice:
    """Tests for Device model."""

    def test_device_creation(self) -> None:
        """Test creating Device object."""
        device: Device = {
            "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)",
            "ip": "192.168.1.1",
            "os": "iOS",
            "osv": "14.0",
        }
        assert device["ua"] == "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)"
        assert device["ip"] == "192.168.1.1"
        assert device["os"] == "iOS"
        assert device["osv"] == "14.0"

    def test_device_ipv6(self) -> None:
        """Test Device with IPv6."""
        device: Device = {
            "ipv6": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "os": "Android",
        }
        assert device["ipv6"] == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"


class TestImp:
    """Tests for Imp (Impression) model."""

    def test_imp_creation(self) -> None:
        """Test creating Imp object."""
        imp: Imp = {
            "id": "imp1",
            "banner": {"w": 300, "h": 250},
            "tagid": "tag123",
            "bidfloor": 0.5,
            "bidfloorcur": "USD",
        }
        assert imp["id"] == "imp1"
        assert imp["banner"] == {"w": 300, "h": 250}
        assert imp["tagid"] == "tag123"
        assert imp["bidfloor"] == 0.5
        assert imp["bidfloorcur"] == "USD"

    def test_imp_with_video(self) -> None:
        """Test Imp with video object."""
        imp: Imp = {
            "id": "imp1",
            "video": {
                "mimes": ["video/mp4"],
                "minduration": 5,
                "maxduration": 30,
            },
        }
        assert imp["video"]["mimes"] == ["video/mp4"]


class TestSite:
    """Tests for Site model."""

    def test_site_creation(self) -> None:
        """Test creating Site object."""
        site: Site = {
            "id": "site123",
            "name": "Example Site",
            "domain": "example.com",
            "page": "https://example.com/article",
        }
        assert site["id"] == "site123"
        assert site["domain"] == "example.com"
        assert site["page"] == "https://example.com/article"


class TestApp:
    """Tests for App model."""

    def test_app_creation(self) -> None:
        """Test creating App object."""
        app: App = {
            "id": "app123",
            "name": "My Game",
            "domain": "mygame.example.com",
        }
        assert app["id"] == "app123"
        assert app["name"] == "My Game"
        assert app["domain"] == "mygame.example.com"


class TestBidRequest:
    """Tests for BidRequest model."""

    def test_bid_request_minimal(self) -> None:
        """Test creating minimal BidRequest."""
        bid_request: BidRequest = {
            "id": "req123",
            "imp": [{"id": "imp1", "banner": {"w": 300, "h": 250}}],
        }
        assert bid_request["id"] == "req123"
        assert len(bid_request["imp"]) == 1
        assert bid_request["imp"][0]["id"] == "imp1"

    def test_bid_request_with_site_device_user(self) -> None:
        """Test BidRequest with site, device, and user."""
        bid_request: BidRequest = {
            "id": "req123",
            "imp": [{"id": "imp1", "banner": {"w": 728, "h": 90}}],
            "site": {"domain": "example.com", "page": "https://example.com/page"},
            "device": {"ua": "Mozilla/5.0", "ip": "192.168.1.1"},
            "user": {"id": "user123"},
        }
        assert bid_request["id"] == "req123"
        assert bid_request["site"]["domain"] == "example.com"
        assert bid_request["device"]["ip"] == "192.168.1.1"
        assert bid_request["user"]["id"] == "user123"

    def test_bid_request_json_serialization(self) -> None:
        """Test BidRequest JSON serialization."""
        bid_request: BidRequest = {
            "id": "req123",
            "imp": [{"id": "imp1", "banner": {"w": 300, "h": 250}}],
            "test": 1,
        }
        json_str = json.dumps(bid_request)
        deserialized = json.loads(json_str)
        assert deserialized["id"] == "req123"
        assert deserialized["test"] == 1


class TestBid:
    """Tests for Bid model."""

    def test_bid_required_fields(self) -> None:
        """Test Bid with required fields."""
        bid: Bid = {
            "impid": "imp1",
            "price": 2.50,
        }
        assert bid["impid"] == "imp1"
        assert bid["price"] == 2.50

    def test_bid_with_markup(self) -> None:
        """Test Bid with ad markup."""
        bid: Bid = {
            "id": "bid123",
            "impid": "imp1",
            "price": 3.00,
            "adm": "<VAST version='3.0'>...</VAST>",
            "adomain": ["advertiser.com"],
        }
        assert bid["id"] == "bid123"
        assert bid["adm"] == "<VAST version='3.0'>...</VAST>"
        assert bid["adomain"] == ["advertiser.com"]


class TestSeatBid:
    """Tests for SeatBid model."""

    def test_seatbid_single_bid(self) -> None:
        """Test SeatBid with single bid."""
        seatbid: SeatBid = {
            "bid": [{"impid": "imp1", "price": 2.00}],
            "seat": "seat123",
        }
        assert len(seatbid["bid"]) == 1
        assert seatbid["seat"] == "seat123"

    def test_seatbid_multiple_bids(self) -> None:
        """Test SeatBid with multiple bids."""
        seatbid: SeatBid = {
            "bid": [
                {"impid": "imp1", "price": 2.00},
                {"impid": "imp2", "price": 3.00},
            ],
        }
        assert len(seatbid["bid"]) == 2


class TestBidResponse:
    """Tests for BidResponse model."""

    def test_bid_response_required_fields(self) -> None:
        """Test BidResponse with required fields."""
        bid_response: BidResponse = {
            "id": "req123",
        }
        assert bid_response["id"] == "req123"

    def test_bid_response_with_seatbids(self) -> None:
        """Test BidResponse with seatbids."""
        bid_response: BidResponse = {
            "id": "req123",
            "seatbid": [
                {
                    "bid": [{"impid": "imp1", "price": 2.50}],
                    "seat": "seat1",
                }
            ],
            "cur": "USD",
        }
        assert bid_response["id"] == "req123"
        assert len(bid_response["seatbid"]) == 1
        assert bid_response["cur"] == "USD"

    def test_bid_response_json_serialization(self) -> None:
        """Test BidResponse JSON serialization."""
        bid_response: BidResponse = {
            "id": "req123",
            "seatbid": [
                {
                    "bid": [{"impid": "imp1", "price": 2.50}],
                }
            ],
        }
        json_str = json.dumps(bid_response)
        deserialized = json.loads(json_str)
        assert deserialized["id"] == "req123"
        assert len(deserialized["seatbid"]) == 1
