"""OpenRTB models unit tests."""

import json

import pytest

from xsp.protocols.openrtb.models import (
    App,
    BidRequest,
    BidResponse,
    Bid,
    Device,
    Imp,
    SeatBid,
    Site,
    User,
)


class TestUser:
    """Test OpenRTB User model."""

    def test_user_creation(self):
        """Test User creation with required fields."""
        user: User = {
            "id": "user123",
        }
        assert user["id"] == "user123"

    def test_user_optional_fields(self):
        """Test User with optional fields."""
        user: User = {
            "id": "user123",
            "buyeruid": "buyer456",
            "gender": "M",
            "yob": 1990,
        }
        assert user["buyeruid"] == "buyer456"
        assert user["gender"] == "M"
        assert user["yob"] == 1990

    def test_user_json_serializable(self):
        """Test User is JSON serializable."""
        user: User = {"id": "user123", "gender": "F"}
        json_str = json.dumps(user)
        parsed = json.loads(json_str)
        assert parsed["id"] == "user123"
        assert parsed["gender"] == "F"


class TestDevice:
    """Test OpenRTB Device model."""

    def test_device_creation(self):
        """Test Device creation."""
        device: Device = {
            "ua": "Mozilla/5.0",
            "ip": "192.168.1.1",
        }
        assert device["ua"] == "Mozilla/5.0"
        assert device["ip"] == "192.168.1.1"

    def test_device_with_os(self):
        """Test Device with OS fields."""
        device: Device = {
            "ua": "Mozilla/5.0",
            "os": "iOS",
            "osv": "14.0",
            "devicetype": 1,  # Mobile
        }
        assert device["os"] == "iOS"
        assert device["osv"] == "14.0"
        assert device["devicetype"] == 1


class TestImp:
    """Test OpenRTB Impression model."""

    def test_imp_required_field(self):
        """Test Imp with required id field."""
        imp: Imp = {"id": "imp-1"}
        assert imp["id"] == "imp-1"

    def test_imp_with_banner(self):
        """Test Imp with banner object."""
        imp: Imp = {
            "id": "imp-1",
            "banner": {"w": 300, "h": 250},
        }
        assert imp["banner"]["w"] == 300
        assert imp["banner"]["h"] == 250

    def test_imp_with_bidfloor(self):
        """Test Imp with bidfloor."""
        imp: Imp = {
            "id": "imp-1",
            "bidfloor": 1.5,
            "bidfloorcur": "USD",
        }
        assert imp["bidfloor"] == 1.5
        assert imp["bidfloorcur"] == "USD"


class TestSite:
    """Test OpenRTB Site model."""

    def test_site_creation(self):
        """Test Site creation."""
        site: Site = {
            "domain": "example.com",
            "page": "https://example.com/article",
        }
        assert site["domain"] == "example.com"
        assert site["page"] == "https://example.com/article"

    def test_site_with_categories(self):
        """Test Site with content categories."""
        site: Site = {
            "domain": "example.com",
            "cat": ["IAB1", "IAB2"],
        }
        assert site["cat"] == ["IAB1", "IAB2"]


class TestApp:
    """Test OpenRTB App model."""

    def test_app_creation(self):
        """Test App creation."""
        app: App = {
            "name": "TestApp",
            "bundle": "com.example.testapp",
        }
        assert app["name"] == "TestApp"
        assert app["bundle"] == "com.example.testapp"


class TestBidRequest:
    """Test OpenRTB BidRequest model."""

    def test_bid_request_required_fields(self):
        """Test BidRequest with required fields."""
        bid_request: BidRequest = {
            "id": "bid-req-001",
            "imp": [{"id": "imp-1"}],
        }
        assert bid_request["id"] == "bid-req-001"
        assert len(bid_request["imp"]) == 1

    def test_bid_request_with_site(self):
        """Test BidRequest with site object."""
        bid_request: BidRequest = {
            "id": "bid-req-001",
            "imp": [{"id": "imp-1", "banner": {"w": 300, "h": 250}}],
            "site": {"domain": "example.com"},
        }
        assert bid_request["site"]["domain"] == "example.com"

    def test_bid_request_with_device_and_user(self):
        """Test BidRequest with device and user."""
        bid_request: BidRequest = {
            "id": "bid-req-001",
            "imp": [{"id": "imp-1"}],
            "device": {"ua": "Mozilla/5.0"},
            "user": {"id": "user123"},
        }
        assert bid_request["device"]["ua"] == "Mozilla/5.0"
        assert bid_request["user"]["id"] == "user123"

    def test_bid_request_json_serializable(self):
        """Test BidRequest is JSON serializable."""
        bid_request: BidRequest = {
            "id": "bid-req-001",
            "imp": [{"id": "imp-1", "banner": {"w": 300, "h": 250}}],
            "site": {"domain": "example.com"},
            "cur": ["USD"],
        }
        json_str = json.dumps(bid_request)
        parsed = json.loads(json_str)
        assert parsed["id"] == "bid-req-001"
        assert parsed["site"]["domain"] == "example.com"


class TestBid:
    """Test OpenRTB Bid model."""

    def test_bid_required_fields(self):
        """Test Bid with required fields."""
        bid: Bid = {
            "impid": "imp-1",
            "price": 2.5,
        }
        assert bid["impid"] == "imp-1"
        assert bid["price"] == 2.5

    def test_bid_with_markup(self):
        """Test Bid with ad markup."""
        bid: Bid = {
            "impid": "imp-1",
            "price": 2.5,
            "adm": "<html><body>Ad</body></html>",
            "adomain": ["advertiser.com"],
        }
        assert "<html>" in bid["adm"]
        assert bid["adomain"] == ["advertiser.com"]


class TestSeatBid:
    """Test OpenRTB SeatBid model."""

    def test_seatbid_creation(self):
        """Test SeatBid creation."""
        seatbid: SeatBid = {
            "bid": [{"impid": "imp-1", "price": 2.5}],
            "seat": "exchange-1",
        }
        assert len(seatbid["bid"]) == 1
        assert seatbid["seat"] == "exchange-1"

    def test_seatbid_multiple_bids(self):
        """Test SeatBid with multiple bids."""
        seatbid: SeatBid = {
            "bid": [
                {"impid": "imp-1", "price": 2.5},
                {"impid": "imp-2", "price": 1.5},
            ],
        }
        assert len(seatbid["bid"]) == 2
        assert seatbid["bid"][0]["price"] == 2.5
        assert seatbid["bid"][1]["price"] == 1.5


class TestBidResponse:
    """Test OpenRTB BidResponse model."""

    def test_bid_response_required_field(self):
        """Test BidResponse with required id field."""
        response: BidResponse = {
            "id": "bid-req-001",
        }
        assert response["id"] == "bid-req-001"

    def test_bid_response_with_seatbids(self):
        """Test BidResponse with seat bids."""
        response: BidResponse = {
            "id": "bid-req-001",
            "seatbid": [
                {
                    "bid": [{"impid": "imp-1", "price": 2.5}],
                    "seat": "exchange-1",
                }
            ],
        }
        assert len(response["seatbid"]) == 1
        assert response["seatbid"][0]["seat"] == "exchange-1"

    def test_bid_response_with_currency(self):
        """Test BidResponse with currency."""
        response: BidResponse = {
            "id": "bid-req-001",
            "cur": "EUR",
        }
        assert response["cur"] == "EUR"

    def test_bid_response_json_serializable(self):
        """Test BidResponse is JSON serializable."""
        response: BidResponse = {
            "id": "bid-req-001",
            "seatbid": [
                {
                    "bid": [{"impid": "imp-1", "price": 2.5}],
                    "seat": "exchange-1",
                }
            ],
            "cur": "USD",
        }
        json_str = json.dumps(response)
        parsed = json.loads(json_str)
        assert parsed["id"] == "bid-req-001"
        assert parsed["seatbid"][0]["seat"] == "exchange-1"
