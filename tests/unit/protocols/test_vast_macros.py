"""Tests for VAST macro substitution."""


from xsp.protocols.vast.macros import MacroSubstitutor


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


def test_macro_substitutor_custom() -> None:
    """Test custom macro registration."""
    sub = MacroSubstitutor()
    sub.register("CUSTOM", lambda: "custom_value")

    url = "https://tracking.example.com/imp?c=[CUSTOM]"
    result = sub.substitute(url)
    assert "[CUSTOM]" not in result
    assert "c=custom_value" in result
