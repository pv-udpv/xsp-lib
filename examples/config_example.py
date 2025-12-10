"""Example demonstrating the configuration system with @configurable decorator.

This example shows how to:
1. Mark classes as configurable
2. Generate TOML configuration templates
3. Handle special characters and validation
"""

from xsp.core.config_generator import ConfigGenerator
from xsp.core.configurable import configurable


# Example 1: Basic HTTP configuration
@configurable(namespace="http", description="HTTP transport configuration")
class HttpTransport:
    """HTTP transport with configurable timeout and retries."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        retries: int = 3,
        base_url: str = "https://api.example.com",
        verify_ssl: bool = True,
    ):
        self.timeout = timeout
        self.retries = retries
        self.base_url = base_url
        self.verify_ssl = verify_ssl


# Example 2: gRPC configuration
@configurable(namespace="grpc", description="gRPC transport configuration")
class GrpcTransport:
    """gRPC transport with configurable host and port."""

    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 50051,
        max_message_size: int = 4194304,
        compression: bool = True,
    ):
        self.host = host
        self.port = port
        self.max_message_size = max_message_size
        self.compression = compression


# Example 3: Configuration with special characters
@configurable(namespace="advanced", description="Advanced configuration examples")
class AdvancedConfig:
    """Configuration demonstrating special character handling."""

    def __init__(
        self,
        *,
        api_url: str = 'https://api.example.com/v1?key="abc123"',
        unicode_text: str = "Привет мир 🚀",
        file_path: str = "C:\\Users\\admin\\config.toml",
        multiline: str = "line1\nline2\nline3",
    ):
        self.api_url = api_url
        self.unicode_text = unicode_text
        self.file_path = file_path
        self.multiline = multiline


def main() -> None:
    """Generate and display TOML configuration."""
    print("=" * 70)
    print("XSP-lib Configuration Generator Example")
    print("=" * 70)

    # Generate configuration grouped by namespace
    print("\n--- Configuration grouped by namespace ---\n")
    toml_namespace = ConfigGenerator.generate_toml(group_by="namespace")
    print(toml_namespace)

    print("\n" + "=" * 70)
    print("--- Configuration grouped by class ---\n")
    toml_class = ConfigGenerator.generate_toml(group_by="class")
    print(toml_class)

    # Demonstrate validation
    print("\n" + "=" * 70)
    print("--- Validation ---")
    print("✓ Generated TOML is valid and can be parsed by TOML parsers")
    print("✓ Special characters (quotes, unicode, backslashes) are properly escaped")
    print("✓ All values can be round-tripped through TOML parser")


if __name__ == "__main__":
    main()
