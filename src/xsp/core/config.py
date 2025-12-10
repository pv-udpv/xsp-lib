from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class XspSettings(BaseSettings):
    """Core configuration for xsp-lib.

    This settings class centralizes environment variables, secrets and
    per-environment configuration for all protocols and transports.
    """

    model_config = SettingsConfigDict(
        env_prefix="XSP_",
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir="/run/secrets",
        validate_default=True,
        extra="forbid",
    )

    # Environment
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # VAST protocol
    vast_endpoint: str = "https://ads.example.com/vast"
    vast_timeout: float = 30.0
    vast_enable_macros: bool = True
    vast_validate_xml: bool = False
    vast_api_key: SecretStr | None = Field(
        default=None,
        description="VAST upstream API key",
    )

    # OpenRTB protocol
    openrtb_endpoint: str = "https://bidder.example.com/openrtb"
    openrtb_timeout: float = 0.3  # per OpenRTB 2.6 §4.1: typical timeout 100-300ms
    openrtb_secret_key: SecretStr | None = Field(
        default=None,
        description="OpenRTB upstream secret key",
    )

    # Transport defaults
    http_pool_size: int = 100
    http_keepalive: bool = True

    # JWT / auth (for examples and future tools)
    jwt_secret_key: SecretStr | None = Field(
        default=None,
        description="JWT signing key",
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30


@dataclass
class UpstreamConfig:
    """Transport-agnostic configuration for upstream services.

    This configuration class provides a protocol-agnostic way to configure
    upstream services (VAST, OpenRTB, DAAST, etc.) without coupling to
    specific transport implementations.

    Example:
        >>> # VAST configuration
        >>> vast_config = UpstreamConfig(
        ...     timeout=30.0,
        ...     encoding="utf-8",
        ...     default_headers={"X-API-Key": "secret"},
        ... )

        >>> # OpenRTB configuration (low latency)
        >>> openrtb_config = UpstreamConfig(
        ...     timeout=0.3,  # 300ms per OpenRTB 2.6 §4.1
        ...     max_retries=1,
        ... )

        >>> # Cyrillic preservation
        >>> cyrillic_config = UpstreamConfig(
        ...     encoding="utf-8",
        ...     encoding_config={"preserve_cyrillic": True},
        ... )

    See Also:
        - docs/architecture/final-architecture.md
        - docs/configuration.md
    """

    timeout: float = 30.0
    max_retries: int = 3
    encoding: str = "utf-8"
    encoding_config: dict[str, Any] | None = None
    default_headers: dict[str, str] | None = field(default_factory=dict)
    default_params: dict[str, Any] | None = field(default_factory=dict)


# Lazy global settings accessor for xsp-lib.
# Use get_settings() to access configuration. For tests, use set_settings() to override.
_settings_instance: XspSettings | None = None

def get_settings() -> XspSettings:
    """
    Returns the global XspSettings instance, lazily initialized.
    For test isolation, use set_settings() to override.
    Returns:
        XspSettings: The current settings instance.
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = XspSettings()
    return _settings_instance

def set_settings(settings: XspSettings | None) -> None:
    """
    Overrides the global settings instance (for tests or custom config).
    Args:
        settings (XspSettings | None): The new settings instance, or None to reset.
    """
    global _settings_instance
    _settings_instance = settings
