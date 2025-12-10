from pathlib import Path

import pytest
from pydantic import ValidationError

from xsp.core.config import XspSettings


@pytest.mark.parametrize(
    "env_value,expected_env",
    [
        (None, "development"),
        ("staging", "staging"),
        ("production", "production"),
    ],
)
def test_xsp_settings_env(
    monkeypatch: pytest.MonkeyPatch, env_value: str | None, expected_env: str
) -> None:
    """Environment is read from XSP_ENV with sensible default."""

    if env_value is not None:
        monkeypatch.setenv("XSP_ENV", env_value)
    else:
        monkeypatch.delenv("XSP_ENV", raising=False)

    settings = XspSettings()

    assert settings.env == expected_env


def test_xsp_settings_env_nested(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nested environment variables are supported via XSP_FOO__BAR pattern for nested models.

    Note: The current config uses flat fields like 'vast_timeout', so we use
    underscore-separated environment variable names (XSP_VAST_TIMEOUT).
    The nested delimiter (__) is configured for future nested model support.
    """

    monkeypatch.setenv("XSP_ENV", "development")
    monkeypatch.setenv("XSP_VAST_TIMEOUT", "42.5")
    monkeypatch.setenv("XSP_VAST_ENABLE_MACROS", "false")

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


def test_xsp_settings_debug_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Debug field is read from XSP_DEBUG with default False."""

    # Test default value
    monkeypatch.delenv("XSP_DEBUG", raising=False)
    settings = XspSettings()
    assert settings.debug is False

    # Test setting to True
    monkeypatch.setenv("XSP_DEBUG", "true")
    settings = XspSettings()
    assert settings.debug is True

    # Test setting to False explicitly
    monkeypatch.setenv("XSP_DEBUG", "false")
    settings = XspSettings()
    assert settings.debug is False


def test_xsp_settings_openrtb_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenRTB configuration fields are properly set."""

    # Test defaults
    monkeypatch.delenv("XSP_OPENRTB_ENDPOINT", raising=False)
    monkeypatch.delenv("XSP_OPENRTB_TIMEOUT", raising=False)
    monkeypatch.delenv("XSP_OPENRTB_SECRET_KEY", raising=False)
    settings = XspSettings()
    assert settings.openrtb_endpoint == "https://bidder.example.com/openrtb"
    assert settings.openrtb_timeout == 100.0
    assert settings.openrtb_secret_key is None

    # Test custom values
    monkeypatch.setenv("XSP_OPENRTB_ENDPOINT", "https://custom-bidder.com/rtb")
    monkeypatch.setenv("XSP_OPENRTB_TIMEOUT", "250.5")
    monkeypatch.setenv("XSP_OPENRTB_SECRET_KEY", "rtb-secret-123")
    settings = XspSettings()
    assert settings.openrtb_endpoint == "https://custom-bidder.com/rtb"
    assert settings.openrtb_timeout == 250.5
    assert settings.openrtb_secret_key is not None
    assert settings.openrtb_secret_key.get_secret_value() == "rtb-secret-123"


def test_xsp_settings_transport_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Transport default fields are properly set."""

    # Test defaults
    monkeypatch.delenv("XSP_HTTP_POOL_SIZE", raising=False)
    monkeypatch.delenv("XSP_HTTP_KEEPALIVE", raising=False)
    settings = XspSettings()
    assert settings.http_pool_size == 100
    assert settings.http_keepalive is True

    # Test custom values
    monkeypatch.setenv("XSP_HTTP_POOL_SIZE", "250")
    monkeypatch.setenv("XSP_HTTP_KEEPALIVE", "false")
    settings = XspSettings()
    assert settings.http_pool_size == 250
    assert settings.http_keepalive is False


def test_xsp_settings_jwt_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """JWT configuration fields are properly set."""

    # Test defaults
    monkeypatch.delenv("XSP_JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("XSP_JWT_ALGORITHM", raising=False)
    monkeypatch.delenv("XSP_JWT_EXPIRE_MINUTES", raising=False)
    settings = XspSettings()
    assert settings.jwt_secret_key is None
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expire_minutes == 30

    # Test custom values
    monkeypatch.setenv("XSP_JWT_SECRET_KEY", "jwt-signing-key-xyz")
    monkeypatch.setenv("XSP_JWT_ALGORITHM", "RS256")
    monkeypatch.setenv("XSP_JWT_EXPIRE_MINUTES", "60")
    settings = XspSettings()
    assert settings.jwt_secret_key is not None
    assert settings.jwt_secret_key.get_secret_value() == "jwt-signing-key-xyz"
    assert settings.jwt_algorithm == "RS256"
    assert settings.jwt_expire_minutes == 60


def test_xsp_settings_env_file_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings can be loaded from .env file."""

    # Create .env file
    # Note: In .env files, nested delimiters don't work the same way as environment variables
    # We use the flat field names as they appear in the model
    env_file = tmp_path / ".env"
    env_file.write_text(
        "XSP_ENV=production\n"
        "XSP_DEBUG=true\n"
        "XSP_VAST_TIMEOUT=99.9\n"
        "XSP_HTTP_POOL_SIZE=500\n"
    )

    # Change to temp directory so .env is found
    monkeypatch.chdir(tmp_path)

    # Clear environment variables to ensure we're loading from .env
    monkeypatch.delenv("XSP_ENV", raising=False)
    monkeypatch.delenv("XSP_DEBUG", raising=False)
    monkeypatch.delenv("XSP_VAST_TIMEOUT", raising=False)
    monkeypatch.delenv("XSP_HTTP_POOL_SIZE", raising=False)

    settings = XspSettings()

    assert settings.env == "production"
    assert settings.debug is True
    assert settings.vast_timeout == 99.9
    assert settings.http_pool_size == 500


def test_xsp_settings_secrets_dir_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Settings can be loaded from /run/secrets directory."""

    # Create secrets directory
    secrets_dir = tmp_path / "run" / "secrets"
    secrets_dir.mkdir(parents=True)

    # Create secret files
    (secrets_dir / "xsp_vast_api_key").write_text("secret-from-file-vast")
    (secrets_dir / "xsp_openrtb_secret_key").write_text("secret-from-file-rtb")

    # Clear environment variables
    monkeypatch.delenv("XSP_VAST_API_KEY", raising=False)
    monkeypatch.delenv("XSP_OPENRTB_SECRET_KEY", raising=False)

    # Create settings with custom secrets_dir
    settings = XspSettings(_secrets_dir=str(secrets_dir))  # type: ignore[call-arg]

    assert settings.vast_api_key is not None
    assert settings.vast_api_key.get_secret_value() == "secret-from-file-vast"
    assert settings.openrtb_secret_key is not None
    assert settings.openrtb_secret_key.get_secret_value() == "secret-from-file-rtb"


def test_xsp_settings_extra_forbid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Extra='forbid' prevents additional fields from being passed directly to model.

    Note: When using environment variables, pydantic-settings filters by prefix (XSP_)
    before passing to the model, so env vars that don't match known fields are silently
    ignored. The extra='forbid' check applies to direct instantiation or .env file parsing.
    """

    # Test that extra fields passed directly to the model raise an error
    with pytest.raises(ValidationError) as exc_info:
        XspSettings(unknown_field="invalid")  # type: ignore

    # Check that the error mentions the unknown field or extra
    error_str = str(exc_info.value).lower()
    assert "unknown_field" in error_str or "extra" in error_str


def test_xsp_settings_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables should be case-insensitive (case_sensitive=False)."""

    # Test with different casings - case_sensitive=False applies to field names
    # but nested delimiter __ may not work with lowercase prefix
    monkeypatch.setenv("xsp_env", "staging")  # lowercase prefix
    monkeypatch.setenv("XSP_DEBUG", "TRUE")  # uppercase value
    monkeypatch.setenv("XSP_VAST_TIMEOUT", "45.0")  # use flat field name for reliability

    settings = XspSettings()

    assert settings.env == "staging"
    assert settings.debug is True
    assert settings.vast_timeout == 45.0
