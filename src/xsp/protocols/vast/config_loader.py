"""YAML configuration loader for VAST chain resolvers.

Loads VAST upstream and chain resolver configurations from YAML files
with support for environment variable substitution.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from xsp.core.transport import Transport

from .chain import ResolutionStrategy, SelectionStrategy, VastChainConfig
from .chain_resolver import VastChainResolver
from .types import VastVersion
from .upstream import VastUpstream


class VastChainConfigLoader:
    """Load VAST chain configurations from YAML files.

    Supports environment variable substitution and creates fully configured
    VastChainResolver instances ready for use.
    """

    @classmethod
    def load(cls, config_path: str | Path, transport: Transport) -> dict[str, VastChainResolver]:
        """Load VAST chain configurations from YAML file.

        Args:
            config_path: Path to YAML configuration file
            transport: Transport instance to use for all upstreams

        Returns:
            Dictionary mapping chain names to VastChainResolver instances

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid or required env vars missing
            yaml.YAMLError: If YAML parsing fails
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        upstreams_config = config.get("upstreams", {})
        if not upstreams_config:
            raise ValueError("Configuration must contain 'upstreams' section")

        upstreams = cls._create_upstreams(upstreams_config, transport)

        chains_config = config.get("chains", {})
        if not chains_config:
            raise ValueError("Configuration must contain 'chains' section")

        resolvers = cls._create_resolvers(chains_config, upstreams)

        return resolvers

    @classmethod
    def _create_upstreams(
        cls, upstreams_config: dict[str, Any], transport: Transport
    ) -> dict[str, VastUpstream]:
        """Create VastUpstream instances from configuration."""
        upstreams: dict[str, VastUpstream] = {}

        for protocol_name, protocol_config in upstreams_config.items():
            if protocol_name == "vast":
                if not isinstance(protocol_config, dict):
                    raise ValueError(f"Invalid upstream config for {protocol_name}")

                for upstream_name, upstream_config in protocol_config.items():
                    if not isinstance(upstream_config, dict):
                        raise ValueError(f"Invalid upstream config for {upstream_name}")

                    endpoint = upstream_config.get("endpoint")
                    if not endpoint:
                        raise ValueError(f"Missing 'endpoint' for upstream {upstream_name}")

                    endpoint = cls._expand_env_vars(str(endpoint))

                    version_str = upstream_config.get("version", "4.2")
                    try:
                        version = VastVersion(version_str)
                    except ValueError:
                        raise ValueError(
                            f"Invalid VAST version '{version_str}' for upstream {upstream_name}"
                        )

                    enable_macros = upstream_config.get("enable_macros", True)
                    validate_xml = upstream_config.get("validate_xml", False)

                    upstream = VastUpstream(
                        transport=transport,
                        endpoint=endpoint,
                        version=version,
                        enable_macros=enable_macros,
                        validate_xml=validate_xml,
                    )

                    qualified_name = f"{protocol_name}.{upstream_name}"
                    upstreams[qualified_name] = upstream

        return upstreams

    @classmethod
    def _create_resolvers(
        cls, chains_config: dict[str, Any], upstreams: dict[str, VastUpstream]
    ) -> dict[str, VastChainResolver]:
        """Create VastChainResolver instances from configuration."""
        resolvers: dict[str, VastChainResolver] = {}

        for chain_name, chain_config in chains_config.items():
            if not isinstance(chain_config, dict):
                raise ValueError(f"Invalid chain config for {chain_name}")

            primary = chain_config.get("primary")
            if not primary:
                raise ValueError(f"Missing 'primary' upstream for chain {chain_name}")

            if primary not in upstreams:
                raise ValueError(f"Primary upstream '{primary}' not found for chain {chain_name}")

            chain_upstreams: dict[str, VastUpstream] = {primary: upstreams[primary]}

            fallbacks = chain_config.get("fallbacks", [])
            if not isinstance(fallbacks, list):
                raise ValueError(f"'fallbacks' must be a list for chain {chain_name}")

            for fallback in fallbacks:
                if fallback not in upstreams:
                    raise ValueError(
                        f"Fallback upstream '{fallback}' not found for chain {chain_name}"
                    )
                chain_upstreams[fallback] = upstreams[fallback]

            config = cls._parse_chain_config(chain_config)

            resolver = VastChainResolver(config=config, upstreams=chain_upstreams)

            resolvers[chain_name] = resolver

        return resolvers

    @classmethod
    def _parse_chain_config(cls, chain_config: dict[str, Any]) -> VastChainConfig:
        """Parse chain configuration into VastChainConfig."""
        resolution_strategy_str = chain_config.get("resolution_strategy", "recursive")
        try:
            resolution_strategy = ResolutionStrategy(resolution_strategy_str)
        except ValueError:
            raise ValueError(f"Invalid resolution_strategy: {resolution_strategy_str}")

        selection_strategy_str = chain_config.get("selection_strategy", "highest_bitrate")
        try:
            selection_strategy = SelectionStrategy(selection_strategy_str)
        except ValueError:
            raise ValueError(f"Invalid selection_strategy: {selection_strategy_str}")

        return VastChainConfig(
            max_depth=chain_config.get("max_depth", 5),
            timeout=chain_config.get("timeout", 30.0),
            per_request_timeout=chain_config.get("per_request_timeout", 10.0),
            enable_fallbacks=chain_config.get("enable_fallbacks", True),
            resolution_strategy=resolution_strategy,
            selection_strategy=selection_strategy,
            follow_redirects=chain_config.get("follow_redirects", True),
            validate_each_response=chain_config.get("validate_each_response", False),
            collect_tracking_urls=chain_config.get("collect_tracking_urls", True),
            collect_error_urls=chain_config.get("collect_error_urls", True),
            additional_params=chain_config.get("additional_params", {}),
        )

    @classmethod
    def _expand_env_vars(cls, value: str) -> str:
        """Expand environment variables in string.

        Supports two patterns:
        - ${VAR} - Required variable, raises ValueError if not set
        - ${VAR:-default} - Optional variable with default value

        Args:
            value: String potentially containing env var patterns

        Returns:
            String with environment variables expanded

        Raises:
            ValueError: If required environment variable is not set
        """
        pattern = r"\$\{([^}:]+)(?::-([^}]+))?\}"

        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default_value = match.group(2)

            env_value = os.environ.get(var_name)

            if env_value is not None:
                return env_value
            elif default_value is not None:
                return default_value
            else:
                raise ValueError(
                    f"Required environment variable '{var_name}' is not set. "
                    f"Set it or provide a default value using ${{VAR:-default}} syntax."
                )

        return re.sub(pattern, replacer, value)
