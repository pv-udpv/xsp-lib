"""AdCOM 1.0 Enumerations.

All enumerated lists from the AdCOM 1.0 specification.
Values are from IAB Tech Lab AdCOM spec.
"""

from enum import IntEnum


class ApiFramework(IntEnum):
    """API Frameworks for interactive media (List 5.6)."""

    VPAID_1_0 = 1
    VPAID_2_0 = 2
    MRAID_1 = 3
    ORMMA = 4
    MRAID_2 = 5
    MRAID_3 = 6
    OMID_1 = 7
    SIMID_1_0 = 8
    SIMID_1_1 = 9


class CreativeAttribute(IntEnum):
    """Creative Attributes (List 5.3)."""

    AUDIO_AD_AUTO_PLAY = 1
    AUDIO_AD_USER_INITIATED = 2
    EXPANDABLE_AUTOMATIC = 3
    EXPANDABLE_USER_INITIATED_CLICK = 4
    EXPANDABLE_USER_INITIATED_ROLLOVER = 5
    IN_BANNER_VIDEO_AD_AUTO_PLAY = 6
    IN_BANNER_VIDEO_AD_USER_INITIATED = 7
    POP = 8
    PROVOCATIVE_OR_SUGGESTIVE = 9
    SHAKY_FLASHING_FLICKERING_EXTREME = 10
    SURVEYS = 11
    TEXT_ONLY = 12
    USER_INTERACTIVE = 13
    WINDOWS_DIALOG_ALERT_STYLE = 14
    HAS_AUDIO_ON_OFF_BUTTON = 15
    AD_CAN_BE_SKIPPED = 16
    FLASH = 17


class EventType(IntEnum):
    """Event Types for tracking (List 5.10)."""

    IMPRESSION = 1
    VIEWABLE_MRC_50 = 2
    VIEWABLE_MRC_100 = 3
    VIEWABLE_VIDEO_50 = 4


class AdPosition(IntEnum):
    """Ad Position (List 5.4)."""

    UNKNOWN = 0
    ABOVE_THE_FOLD = 1
    DEPRECATED_LIKELY_ABOVE_FOLD = 2  # Deprecated
    BELOW_THE_FOLD = 3
    HEADER = 4
    FOOTER = 5
    SIDEBAR = 6
    FULLSCREEN = 7


class VideoPlacementType(IntEnum):
    """Video Placement Types (List 5.9)."""

    IN_STREAM = 1
    IN_BANNER = 2
    IN_ARTICLE = 3
    IN_FEED = 4
    INTERSTITIAL_SLIDER_FLOATING = 5


class PlaybackMethod(IntEnum):
    """Video Playback Methods (List 5.10)."""

    PAGE_LOAD_SOUND_ON = 1
    PAGE_LOAD_SOUND_OFF = 2
    CLICK_SOUND_ON = 3
    MOUSE_OVER_SOUND_ON = 4
    ENTERING_VIEWPORT_SOUND_ON = 5
    ENTERING_VIEWPORT_SOUND_OFF = 6


class PlaybackCessationMode(IntEnum):
    """Playback Cessation Modes (List 5.11)."""

    ON_VIDEO_COMPLETION = 1
    ON_LEAVING_VIEWPORT = 2
    ON_LEAVING_VIEWPORT_CONTINUES = 3


class CategoryTaxonomy(IntEnum):
    """Content Category Taxonomies (List 5.1)."""

    IAB_CONTENT_CATEGORY_1_0 = 1
    IAB_CONTENT_CATEGORY_2_0 = 2
    IAB_AD_PRODUCT_TAXONOMY_1_0 = 3
    IAB_CONTENT_TAXONOMY_2_1 = 4
    IAB_CONTENT_TAXONOMY_2_2 = 5
    IAB_CONTENT_TAXONOMY_3_0 = 6


class ContentContext(IntEnum):
    """Content Context (List 5.18)."""

    VIDEO = 1
    GAME = 2
    MUSIC = 3
    APPLICATION = 4
    TEXT = 5
    OTHER = 6
    UNKNOWN = 7


class QAGMediaRating(IntEnum):
    """QAG Media Ratings (List 5.19)."""

    ALL_AUDIENCES = 1
    EVERYONE_OVER_12 = 2
    MATURE_AUDIENCES = 3


class LocationType(IntEnum):
    """Location Types (List 5.20)."""

    GPS_LOCATION = 1
    IP_ADDRESS = 2
    USER_PROVIDED = 3


class DeviceType(IntEnum):
    """Device Types (List 5.21)."""

    MOBILE_TABLET = 1
    PERSONAL_COMPUTER = 2
    CONNECTED_TV = 3
    PHONE = 4
    TABLET = 5
    CONNECTED_DEVICE = 6
    SET_TOP_BOX = 7


class ConnectionType(IntEnum):
    """Connection Types (List 5.22)."""

    UNKNOWN = 0
    ETHERNET = 1
    WIFI = 2
    CELLULAR_UNKNOWN = 3
    CELLULAR_2G = 4
    CELLULAR_3G = 5
    CELLULAR_4G = 6


class DOOHVenueType(IntEnum):
    """DOOH Venue Types (List 5.24)."""

    AIRBORNE = 1
    AIRPORT_GENERAL = 2
    AIRPORT_BAGGAGE_CLAIM = 3
    AIRPORT_TERMINAL = 4
    AIRPORT_LOUNGE = 5
    ATM = 6
    BACKLIGHT = 7
    BAR = 8
    BENCH = 9
    BIKE_RACK = 10
    BULLETIN_BOARD = 11
    BUS = 12
    CAFE = 13
    CASUAL_DINING = 14
    CHILD_CARE = 15
    CINEMA = 16
    CITY_INFORMATION_PANEL = 17
    CONVENIENCE_STORE = 18
    DEDICATED_WILD_POSTING = 19
    DOCTOR_OFFICE_GENERAL = 20
    DOCTOR_OFFICE_OBSTETRICS = 21
    DOCTOR_OFFICE_PEDIATRICS = 22
    FAMILY_ENTERTAINMENT = 23
    FERRY = 24
    FINANCIAL_SERVICES = 25
    GAS_STATION = 26
    GOLF_CART = 27
    GYM = 28
    HOSPITAL = 29
    HOTEL = 30
    JUNIOR_POSTER = 31
    KIOSK = 32
    MALL_GENERAL = 33
    MALL_FOOD_COURT = 34
    MARINE = 35
    MOBILE_BILLBOARD = 36
    MOVIE_THEATER_LOBBY = 37
    NEWSSTAND = 38
    OFFICE_BUILDING = 39
    PARKING_GARAGE = 40
    PEDESTRIAN_WALKWAY = 41
    PHARMACY = 42
    POSTER = 43
    QUICK_SERVICE_RESTAURANT = 44
    RAIL = 45
    RECEPTACLE = 46
    RECREATION_FISHING = 47
    RECREATION_GENERAL = 48
    RECREATION_SKIING = 49
    RECYCLING = 50
    RESIDENTIAL = 51
    RETAIL = 52
    SALON = 53
    SHELTER = 54
    SPORTS_ENTERTAINMENT = 55
    STREET_FURNITURE = 56
    SUBWAY = 57
    TAXI_RIDESHARE = 58
    TRUCKSIDE = 59
    UNIVERSITY = 60
    URBAN_PANEL = 61
    VETERINARIAN = 62
    WALL_SPECTACULAR = 63
    OTHER = 64


class MediaRating(IntEnum):
    """Media Ratings (List 5.25)."""

    UNKNOWN = 0
    ALL_AUDIENCES = 1
    EVERYONE_OVER_12 = 2
    MATURE_AUDIENCES = 3


class LinearityMode(IntEnum):
    """Video Linearity (List 5.7)."""

    LINEAR = 1
    NON_LINEAR = 2


class DeliveryMethod(IntEnum):
    """Content Delivery Methods (List 5.15)."""

    STREAMING = 1
    PROGRESSIVE = 2
    DOWNLOAD = 3


class FeedType(IntEnum):
    """Feed Types (List 5.16)."""

    MUSIC = 1
    BROADCAST = 2
    PODCAST = 3


class VolumeNormalizationMode(IntEnum):
    """Volume Normalization Modes (List 5.17)."""

    NONE = 0
    AVG_VOLUME = 1
    PEAK_VOLUME = 2
    LOUDNESS = 3
    CUSTOM_VOLUME = 4


class ProductionQuality(IntEnum):
    """Production Quality (List 5.13)."""

    UNKNOWN = 0
    PROFESSIONAL = 1
    PROSUMER = 2
    USER_GENERATED = 3


class CompanionType(IntEnum):
    """Companion Types (List 5.14)."""

    STATIC = 1
    HTML = 2
    IFRAME = 3


class NativeDataAssetType(IntEnum):
    """Native Data Asset Types (List 5.8)."""

    SPONSORED = 1
    DESC = 2
    RATING = 3
    LIKES = 4
    DOWNLOADS = 5
    PRICE = 6
    SALEPRICE = 7
    PHONE = 8
    ADDRESS = 9
    DESC2 = 10
    DISPLAYURL = 11
    CTATEXT = 12


class EventTrackingMethod(IntEnum):
    """Event Tracking Methods (List 5.11)."""

    IMAGE_PIXEL = 1
    JAVASCRIPT = 2


class ExpandableDirection(IntEnum):
    """Expandable Ad Directions (List 5.5)."""

    LEFT = 1
    RIGHT = 2
    UP = 3
    DOWN = 4
    FULLSCREEN = 5


class ClickType(IntEnum):
    """Click Types (List 5.26)."""

    NON_CLICKABLE = 0
    CLICKABLE = 1


class AuditStatusCode(IntEnum):
    """Audit Status Codes (List 5.27)."""

    PENDING_AUDIT = 1
    PRE_APPROVED = 2
    APPROVED = 3
    DENIED = 4
    CHANGED_RESUBMIT = 5
