from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass
class UpstreamConfig:
    """Transport-agnostic upstream configuration.

    Provides a reusable configuration structure for upstream services that
    can be used across different transport implementations (HTTP, gRPC, etc.)
    and AdTech protocols (VAST, OpenRTB, etc.).

    This dataclass separates configuration concerns from transport logic,
    enabling better testability and flexibility when integrating with
    different upstream services.

    Attributes:
        endpoint: Base URL or endpoint for the upstream service
            (e.g., "https://ads.example.com/vast" or "grpc://bidder:50051")
        params: Default query parameters to include in all requests.
            Can be overridden per-request via merge_params().
        headers: Default HTTP headers to include in all requests.
            Can be overridden per-request via merge_headers().
        encoding_config: Encoding preservation configuration for special character sets.
            Example: {"preserve_cyrillic": True} to maintain Cyrillic characters
            in URL parameters without percent-encoding per IAB URL encoding guidelines.
        timeout: Request timeout in seconds. Per OpenRTB 2.6 §4.1, typical
            timeouts are 100-300ms for RTB and 30s for VAST.
        max_retries: Maximum number of retry attempts for failed requests.
            Retries use exponential backoff with jitter.

    Example:
        >>> # VAST upstream configuration
        >>> vast_config = UpstreamConfig(
        ...     endpoint="https://ads.example.com/vast",
        ...     params={"app": "myapp", "version": "1.0"},
        ...     headers={"User-Agent": "MyApp/1.0", "Accept": "application/xml"},
        ...     encoding_config={"preserve_cyrillic": True},
        ...     timeout=30.0,
        ...     max_retries=3
        ... )
        >>>
        >>> # OpenRTB upstream configuration (shorter timeout per spec)
        >>> rtb_config = UpstreamConfig(
        ...     endpoint="https://bidder.example.com/openrtb",
        ...     params={"publisher": "pub123"},
        ...     headers={"Content-Type": "application/json"},
        ...     timeout=0.3,  # 300ms per OpenRTB 2.6 §4.1
        ...     max_retries=1
        ... )
        >>>
        >>> # Merge request-specific params
        >>> request_params = vast_config.merge_params({"w": "640", "h": "480"})
        >>> # Returns: {"app": "myapp", "version": "1.0", "w": "640", "h": "480"}
        >>>
        >>> # Create modified config with replace()
        >>> dev_config = vast_config.replace(endpoint="https://dev.example.com/vast")

    References:
        - OpenRTB 2.6 §4.1: Typical bid request timeout is 100-300ms
        - VAST 4.2: Wrapper resolution typically allows 30s total timeout
        - IAB URL Encoding Guidelines: Cyrillic preservation for international markets
    """

    endpoint: str
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    encoding_config: dict[str, bool] = field(default_factory=dict)
    timeout: float = 30.0
    max_retries: int = 3

    def replace(self, **kwargs: Any) -> UpstreamConfig:
        """Create a new UpstreamConfig with specified fields replaced.

        This method enables immutable-style updates by creating a new config
        instance with modified values, leaving the original unchanged.

        Args:
            **kwargs: Fields to replace with new values. Valid keys are:
                endpoint, params, headers, encoding_config, timeout, max_retries

        Returns:
            New UpstreamConfig instance with replaced values

        Raises:
            TypeError: If kwargs contains invalid field names

        Example:
            >>> config = UpstreamConfig(endpoint="https://example.com", timeout=30.0)
            >>> dev_config = config.replace(endpoint="https://dev.example.com")
            >>> prod_config = config.replace(timeout=10.0, max_retries=5)
            >>>
            >>> # Original config is unchanged
            >>> assert config.endpoint == "https://example.com"
            >>> assert dev_config.endpoint == "https://dev.example.com"
        """
        # Get current field values with proper types
        endpoint: str = kwargs.get("endpoint", self.endpoint)
        params: dict[str, Any] = kwargs.get("params", self.params.copy())
        headers: dict[str, str] = kwargs.get("headers", self.headers.copy())
        encoding_config: dict[str, bool] = kwargs.get(
            "encoding_config", self.encoding_config.copy()
        )
        timeout: float = kwargs.get("timeout", self.timeout)
        max_retries: int = kwargs.get("max_retries", self.max_retries)

        # Copy dict fields if not provided in kwargs to ensure independence
        if "params" not in kwargs:
            params = self.params.copy()
        if "headers" not in kwargs:
            headers = self.headers.copy()
        if "encoding_config" not in kwargs:
            encoding_config = self.encoding_config.copy()

        return UpstreamConfig(
            endpoint=endpoint,
            params=params,
            headers=headers,
            encoding_config=encoding_config,
            timeout=timeout,
            max_retries=max_retries,
        )

    def merge_params(self, params: dict[str, Any] | None) -> dict[str, Any]:
        """Merge request-specific params with default params.

        Request params override default params when keys conflict.
        Original config params dict is not modified.

        Args:
            params: Request-specific parameters to merge. None is treated as empty dict.

        Returns:
            Merged parameter dictionary with request params taking precedence

        Example:
            >>> config = UpstreamConfig(
            ...     endpoint="https://example.com",
            ...     params={"app": "myapp", "version": "1.0", "debug": "false"}
            ... )
            >>> merged = config.merge_params({"width": "640", "debug": "true"})
            >>> # Returns: {"app": "myapp", "version": "1.0", "debug": "true", "width": "640"}
            >>> assert merged["debug"] == "true"  # Request param overrides default
            >>> assert merged["app"] == "myapp"   # Default param preserved
            >>> assert config.params["debug"] == "false"  # Original unchanged
        """
        merged = self.params.copy()
        if params is not None:
            merged.update(params)
        return merged

    def merge_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        """Merge request-specific headers with default headers.

        Request headers override default headers when keys conflict.
        Original config headers dict is not modified.

        Args:
            headers: Request-specific headers to merge. None is treated as empty dict.

        Returns:
            Merged headers dictionary with request headers taking precedence

        Example:
            >>> config = UpstreamConfig(
            ...     endpoint="https://example.com",
            ...     headers={"User-Agent": "MyApp/1.0", "Accept": "application/xml"}
            ... )
            >>> merged = config.merge_headers({"Authorization": "Bearer token123"})
            >>> # Returns: {"User-Agent": "MyApp/1.0", "Accept": "application/xml",
            >>> #          "Authorization": "Bearer token123"}
            >>>
            >>> # Override default header
            >>> merged = config.merge_headers({"User-Agent": "MyApp/2.0"})
            >>> assert merged["User-Agent"] == "MyApp/2.0"  # Request header overrides
            >>> assert config.headers["User-Agent"] == "MyApp/1.0"  # Original unchanged
        """
        merged = self.headers.copy()
        if headers is not None:
            merged.update(headers)
        return merged


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
