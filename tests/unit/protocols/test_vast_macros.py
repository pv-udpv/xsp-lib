"""Tests for VAST macro substitution."""


from xsp.protocols.vast.macros import MacroSubstitutor
from xsp.protocols.vast.types import VastVersion


def test_macro_substitutor_timestamp() -> None:
    """Test TIMESTAMP macro."""
    sub = MacroSubstitutor()
    url = "https://tracking.example.com/imp?ts=[TIMESTAMP]"

    result = sub.substitute(url)
    assert "[TIMESTAMP]" not in result
    assert "ts=" in result


def test_macro_substitutor_cachebusting() -> None:
    """Test CACHEBUSTING macro."""
    sub = MacroSubstitutor()
    url = "https://tracking.example.com/imp?cb=[CACHEBUSTING]"

    result = sub.substitute(url)
    assert "[CACHEBUSTING]" not in result
    assert "cb=" in result


def test_macro_substitutor_context() -> None:
    """Test context-based macro substitution."""
    sub = MacroSubstitutor()
    url = "https://tracking.example.com/imp?playhead=[CONTENTPLAYHEAD]&error=[ERRORCODE]"

    result = sub.substitute(
        url, context={"CONTENTPLAYHEAD": "00:01:30", "ERRORCODE": "900"}
    )
    assert "[CONTENTPLAYHEAD]" not in result
    assert "[ERRORCODE]" not in result
    assert "playhead=" in result
    assert "error=" in result


def test_macro_substitutor_context_case_insensitive() -> None:
    """Test context keys are case-insensitive."""
    sub = MacroSubstitutor()
    url = "https://tracking.example.com/imp?playhead=[CONTENTPLAYHEAD]"

    # Test lowercase context key
    result1 = sub.substitute(url, context={"contentplayhead": "10.5"})
    assert "[CONTENTPLAYHEAD]" not in result1
    assert "playhead=10.5" in result1

    # Test mixed case context key
    result2 = sub.substitute(url, context={"ContentPlayHead": "10.5"})
    assert "[CONTENTPLAYHEAD]" not in result2
    assert "playhead=10.5" in result2

    # Test uppercase context key
    result3 = sub.substitute(url, context={"CONTENTPLAYHEAD": "10.5"})
    assert "[CONTENTPLAYHEAD]" not in result3
    assert "playhead=10.5" in result3


def test_macro_substitutor_custom() -> None:
    """Test custom macro registration."""
    sub = MacroSubstitutor()
    sub.register("CUSTOM", lambda: "custom_value")

    url = "https://tracking.example.com/imp?c=[CUSTOM]"
    result = sub.substitute(url)
    assert "[CUSTOM]" not in result
    assert "c=custom_value" in result


def test_macro_substitutor_version_filtering_v30() -> None:
    """Test VAST 3.0 filters out 4.x macros."""
    sub_30 = MacroSubstitutor(version=VastVersion.V3_0)
    url = "https://tracking.example.com/imp?ua=[SERVERUA]&ts=[TIMESTAMP]"

    result = sub_30.substitute(url)
    # SERVERUA is 4.1+, should not be substituted
    assert "[SERVERUA]" in result
    # TIMESTAMP is 2.0+, should be substituted
    assert "[TIMESTAMP]" not in result


def test_macro_substitutor_version_filtering_v42() -> None:
    """Test VAST 4.2 includes all macros."""
    sub_42 = MacroSubstitutor(version=VastVersion.V4_2)
    url = "https://tracking.example.com/imp?ua=[SERVERUA]&ts=[TIMESTAMP]"

    result = sub_42.substitute(url, context={"serverua": "test-agent"})
    # Both should be substituted
    assert "[SERVERUA]" not in result
    assert "[TIMESTAMP]" not in result
    assert "ua=test-agent" in result


def test_macro_substitutor_ssai_mode_enabled() -> None:
    """Test SSAI mode filters out non-recommended macros."""
    sub = MacroSubstitutor(version=VastVersion.V4_2, ssai_mode=True)
    url = "https://tracking.example.com/imp?asset=[ASSETURI]&ts=[TIMESTAMP]&err=[ERRORCODE]"

    result = sub.substitute(
        url, context={"asseturi": "video.mp4", "errorcode": "900"}
    )
    # TIMESTAMP is SSAI-recommended, should be substituted
    assert "[TIMESTAMP]" not in result
    # ASSETURI and ERRORCODE are not SSAI-recommended, should not be substituted
    assert "[ASSETURI]" in result
    assert "[ERRORCODE]" in result


def test_macro_substitutor_ssai_mode_disabled() -> None:
    """Test SSAI mode disabled includes all version-compatible macros."""
    sub = MacroSubstitutor(version=VastVersion.V4_2, ssai_mode=False)
    url = "https://tracking.example.com/imp?asset=[ASSETURI]&ts=[TIMESTAMP]&err=[ERRORCODE]"

    result = sub.substitute(
        url, context={"asseturi": "video.mp4", "errorcode": "900"}
    )
    # All should be substituted
    assert "[TIMESTAMP]" not in result
    assert "[ASSETURI]" not in result
    assert "[ERRORCODE]" not in result


def test_macro_substitutor_url_encoding() -> None:
    """Test URL-safe characters are preserved in encoding."""
    sub = MacroSubstitutor()
    url = "https://tracking.example.com/imp?val=[CUSTOM]"

    # Test that URL-safe characters like - _ . ~ are not encoded
    sub.register("CUSTOM", lambda: "test-value_123.456~end")
    result = sub.substitute(url)

    # These characters should not be percent-encoded
    assert "test-value_123.456~end" in result
    assert "%2D" not in result  # - should not be encoded
    assert "%5F" not in result  # _ should not be encoded
    assert "%2E" not in result  # . should not be encoded
    assert "%7E" not in result  # ~ should not be encoded
