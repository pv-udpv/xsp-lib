#!/usr/bin/env python
"""Demo of @configurable decorator usage."""

import asyncio
from xsp.core.configurable import configurable, get_configurable_registry
from xsp.core.config_generator import ConfigGenerator


@configurable(
    namespace="demo",
    description="Demo service for configuration example"
)
class DemoService:
    """Example service with configurable parameters."""

    def __init__(
        self,
        name: str,  # Required positional arg (not in config)
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        enabled: bool = True,
        api_url: str = "https://api.example.com",
    ):
        """
        Initialize demo service.

        Args:
            name: Service name (required)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            enabled: Enable/disable service
            api_url: API endpoint URL
        """
        self.name = name
        self.timeout = timeout
        self.max_retries = max_retries
        self.enabled = enabled
        self.api_url = api_url

    async def fetch(self) -> str:
        """Fetch data from service."""
        if not self.enabled:
            return "Service disabled"

        # Simulate async operation
        await asyncio.sleep(0.1)
        return f"Fetched from {self.api_url} (timeout: {self.timeout}s)"


async def main():
    """Demo script."""
    print("=" * 60)
    print("@configurable Decorator Demo")
    print("=" * 60)
    print()

    # Create service instance
    service = DemoService(
        "test-service",
        timeout=60.0,
        max_retries=5,
    )

    # Use service
    result = await service.fetch()
    print(f"Result: {result}")
    print()

    # Show registered configurables
    print("=" * 60)
    print("Registered Configurables")
    print("=" * 60)
    print()

    registry = get_configurable_registry()
    for key, metadata in registry.items():
        print(f"Class: {key}")
        print(f"  Namespace: {metadata.namespace}")
        print(f"  Description: {metadata.description}")
        print(f"  Parameters: {len(metadata.parameters)}")
        for param_name, param_info in metadata.parameters.items():
            print(f"    - {param_name}: {param_info.type_hint} = {param_info.default}")
        print()

    # Generate TOML config
    print("=" * 60)
    print("Generated TOML Configuration")
    print("=" * 60)
    print()

    toml = ConfigGenerator.generate_toml()
    print(toml)


if __name__ == "__main__":
    asyncio.run(main())
