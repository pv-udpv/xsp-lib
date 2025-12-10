from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass
class UpstreamConfig:
    """
    Transport-agnostic upstream configuration.

    Separates configuration from transport implementation,
    enabling easy switching between HTTP/gRPC/WebSocket/file transports.

    Attributes:
        endpoint: Upstream service URL or path
        params: Default query parameters
        headers: Default HTTP headers
        encoding_config: Parameter encoding rules (e.g., preserve Cyrillic)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Example:
        ```python
        # VAST upstream config
        config = UpstreamConfig(
            endpoint="https://ads.example.com/vast",
            params={"publisher_id": "pub123"},
            headers={"User-Agent": "xsp-lib/1.0"},
            encoding_config={"url": False},  # Preserve Cyrillic in URL
            timeout=30.0,
            max_retries=3
        )

        # Use with different transports
        http_upstream = VastUpstream(
            transport=HttpTransport(),
            config=config
        )

        # Or file-based for testing
        file_upstream = VastUpstream(
            transport=FileTransport(),
            config=config.replace(endpoint="/path/to/vast.xml")
        )
        ```
    """

    endpoint: str
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    encoding_config: dict[str, bool] = field(default_factory=dict)
    timeout: float = 30.0
    max_retries: int = 3

    def replace(self, **kwargs: Any) -> "UpstreamConfig":
        """
        Create new config with updated fields.

        Example:
            ```python
            prod_config = base_config.replace(
                endpoint="https://prod.example.com/vast",
                timeout=60.0
            )
            ```
        """
        return replace(self, **kwargs)

    def merge_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Merge request params with defaults.

        Request params override config params.

        Args:
            params: Request-specific parameters

        Returns:
            Merged parameters
        """
        return {**self.params, **params}

    def merge_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """
        Merge request headers with defaults.

        Request headers override config headers.

        Args:
            headers: Request-specific headers

        Returns:
            Merged headers
        """
        return {**self.headers, **headers}


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
