
import pytest

from xsp.core.config import XspSettings


@pytest.mark.parametrize("env_value,expected_env", [
    (None, "development"),
    ("staging", "staging"),
    ("production", "production"),
])
def test_xsp_settings_env(monkeypatch: pytest.MonkeyPatch, env_value: str | None, expected_env: str) -> None:
    """Environment is read from XSP_ENV with sensible default."""

    if env_value is not None:
        monkeypatch.setenv("XSP_ENV", env_value)
    else:
        monkeypatch.delenv("XSP_ENV", raising=False)

    settings = XspSettings()

    assert settings.env == expected_env


def test_xsp_settings_env_nested(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nested environment variables are supported via XSP_FOO__BAR pattern."""

    monkeypatch.setenv("XSP_ENV", "development")
    monkeypatch.setenv("XSP_VAST__TIMEOUT", "42.5")
    monkeypatch.setenv("XSP_VAST__ENABLE_MACROS", "false")

    settings = XspSettings()

    assert settings.vast_timeout == 42.5
    assert settings.vast_enable_macros is False


def test_xsp_settings_secrets_masked_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secret values should not be visible in repr()."""

    monkeypatch.setenv("XSP_VAST_API_KEY", "super-secret")
    settings = XspSettings()

    text = repr(settings)

    assert "super-secret" not in text
    assert "vast_api_key" in text
