"""Tests for AdCOM utility functions."""

import pytest

from xsp.standards.adcom.media import Ad, Display
from xsp.standards.adcom.utils import get_ext, has_ext, merge_ext, set_ext


def test_get_ext_existing_key() -> None:
    """Test getting existing extension value."""
    display = Display(mime="image/jpeg", ext={"vendor": "data"})

    value = get_ext(display, "vendor")
    assert value == "data"


def test_get_ext_missing_key() -> None:
    """Test getting missing extension key returns default."""
    display = Display(mime="image/jpeg", ext={"vendor": "data"})

    value = get_ext(display, "missing", default="default_value")
    assert value == "default_value"


def test_get_ext_no_ext_field() -> None:
    """Test getting from object without ext field."""
    display = Display(mime="image/jpeg")

    value = get_ext(display, "key", default="default")
    assert value == "default"


def test_set_ext() -> None:
    """Test setting extension value."""
    display = Display(mime="image/jpeg")

    set_ext(display, "vendor", "value")
    assert display.ext["vendor"] == "value"


def test_set_ext_existing() -> None:
    """Test setting extension value on existing ext."""
    display = Display(mime="image/jpeg", ext={"existing": "data"})

    set_ext(display, "new", "value")
    assert display.ext["new"] == "value"
    assert display.ext["existing"] == "data"


def test_set_ext_no_ext_field() -> None:
    """Test setting extension on object without ext field raises error."""

    class NoExtObject:
        pass

    obj = NoExtObject()
    with pytest.raises(ValueError, match="does not have ext field"):
        set_ext(obj, "key", "value")


def test_merge_ext() -> None:
    """Test merging extensions."""
    display = Display(mime="image/jpeg", ext={"existing": "data"})

    merge_ext(display, {"new1": "value1", "new2": "value2"})

    assert display.ext["existing"] == "data"
    assert display.ext["new1"] == "value1"
    assert display.ext["new2"] == "value2"


def test_merge_ext_overwrite() -> None:
    """Test merging extensions overwrites existing keys."""
    display = Display(mime="image/jpeg", ext={"key": "old"})

    merge_ext(display, {"key": "new"})

    assert display.ext["key"] == "new"


def test_merge_ext_no_existing() -> None:
    """Test merging extensions on object without ext."""
    display = Display(mime="image/jpeg")

    merge_ext(display, {"key": "value"})

    assert display.ext["key"] == "value"


def test_has_ext_true() -> None:
    """Test checking for existing extension key."""
    display = Display(mime="image/jpeg", ext={"vendor": "data"})

    assert has_ext(display, "vendor") is True


def test_has_ext_false() -> None:
    """Test checking for missing extension key."""
    display = Display(mime="image/jpeg", ext={"vendor": "data"})

    assert has_ext(display, "missing") is False


def test_has_ext_no_ext() -> None:
    """Test checking extension on object without ext field."""
    display = Display(mime="image/jpeg")

    assert has_ext(display, "key") is False


def test_ext_workflow() -> None:
    """Test complete workflow with extension utilities."""
    display = Display(mime="image/jpeg")

    # Initially no ext
    assert has_ext(display, "vendor") is False

    # Set extension
    set_ext(display, "vendor", "vendor1")
    assert has_ext(display, "vendor") is True
    assert get_ext(display, "vendor") == "vendor1"

    # Merge more extensions
    merge_ext(display, {"ssp": "ssp1", "dsp": "dsp1"})
    assert get_ext(display, "ssp") == "ssp1"
    assert get_ext(display, "dsp") == "dsp1"
    assert get_ext(display, "vendor") == "vendor1"

    # Update existing
    set_ext(display, "vendor", "vendor2")
    assert get_ext(display, "vendor") == "vendor2"
