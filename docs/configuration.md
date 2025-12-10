# Configuration System

The xsp-lib configuration system provides a type-safe way to generate TOML configuration templates from your code. It uses the `@configurable` decorator to mark classes that should be included in configuration files.

## Overview

The configuration system consists of:

1. **@configurable decorator**: Marks classes and their parameters for configuration
2. **ConfigGenerator**: Generates TOML templates from the registry
3. **Built-in TOML validation**: Ensures generated configuration is always valid

## Quick Start

### 1. Mark Classes as Configurable

Use the `@configurable` decorator on classes with keyword-only parameters:

```python
from xsp.core.configurable import configurable

@configurable(namespace="http", description="HTTP transport settings")
class HttpTransport:
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
```

### 2. Generate TOML Configuration

Generate a configuration template programmatically:

```python
from xsp.core.config_generator import ConfigGenerator

# Generate TOML template
toml_template = ConfigGenerator.generate_toml(group_by="namespace")
print(toml_template)
```

Output:

```toml
# XSP-lib Configuration Template
# Auto-generated from @configurable registry

[http]
# HTTP transport settings
# Source: HttpTransport

# Type: float
timeout = 30.0

# Type: int
retries = 3

# Type: str
base_url = "https://api.example.com"

# Type: bool
verify_ssl = true
```

### 3. Use the CLI Tool

Generate configuration from the command line:

```bash
# Generate to stdout
python -m xsp.cli.generate_config

# Generate to file
python -m xsp.cli.generate_config --output settings.toml

# Group by class instead of namespace
python -m xsp.cli.generate_config --group-by class

# Skip validation (faster, but less safe)
python -m xsp.cli.generate_config --no-validate
```

## Features

### Automatic Type Extraction

The decorator automatically extracts parameter types and defaults:

```python
@configurable(namespace="database")
class DatabaseConfig:
    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 5432,
        pool_size: int = 10,
        timeout: float = 30.0,
        ssl_enabled: bool = False,
    ):
        pass
```

### TOML Validation

All generated TOML is automatically validated by parsing it back. This ensures:

- Strings with quotes are properly escaped
- Unicode characters are handled correctly
- Special characters (newlines, tabs, backslashes) work as expected
- Invalid TOML structures are caught immediately

```python
@configurable(namespace="test")
class TestClass:
    def __init__(
        self,
        *,
        url: str = 'http://example.com?a="test"',  # Quotes handled
        unicode: str = "Привет мир 🚀",              # Unicode preserved
        path: str = "C:\\Users\\test\\path",         # Backslashes escaped
        multiline: str = "line1\nline2",             # Newlines handled
    ):
        pass

# Generate and validate
toml_str = ConfigGenerator.generate_toml(validate=True)
```

### Handling Special Characters

The system properly handles all TOML edge cases:

| Type | Example | TOML Output |
|------|---------|-------------|
| Quotes | `'test "quoted" string'` | `"test \"quoted\" string"` |
| Backslashes | `"C:\\path\\to\\file"` | `"C:\\path\\to\\file"` |
| Unicode | `"Привет мир 🚀"` | `"Привет мир 🚀"` |
| Newlines | `"line1\nline2"` | `"line1\nline2"` |
| Tabs | `"col1\tcol2"` | `"col1\tcol2"` |

### None Values

Python `None` values are handled as commented-out entries:

```python
@configurable(namespace="optional")
class OptionalConfig:
    def __init__(self, *, api_key: str | None = None):
        pass
```

Generates:

```toml
[optional]
# Type: str | None
# api_key = null  # None value
```

### Grouping Options

#### Group by Namespace (Default)

Groups all classes by their namespace:

```python
@configurable(namespace="http")
class HttpTransport:
    def __init__(self, *, timeout: float = 30.0):
        pass

@configurable(namespace="http")
class HttpClient:
    def __init__(self, *, retries: int = 3):
        pass
```

Generates:

```toml
[http]
# Source: HttpTransport
# Type: float
timeout = 30.0

# Source: HttpClient
# Type: int
retries = 3
```

#### Group by Class

Groups each class in its own section:

```python
toml_str = ConfigGenerator.generate_toml(group_by="class")
```

Generates:

```toml
[http.HttpTransport]
# Type: float
timeout = 30.0

[http.HttpClient]
# Type: int
retries = 3
```

## Advanced Usage

### Registry Management

```python
from xsp.core.configurable import (
    get_configurable_registry,
    clear_configurable_registry,
)

# Get current registry
registry = get_configurable_registry()

# Clear registry (useful for testing)
clear_configurable_registry()
```

### Custom Validation

```python
# Generate without validation (faster)
toml_str = ConfigGenerator.generate_toml(validate=False)

# Manually validate
from xsp.core.config_generator import ConfigGenerator
ConfigGenerator._validate_toml(toml_str)
```

### Accessing Metadata

```python
from xsp.core.configurable import get_configurable_registry

registry = get_configurable_registry()
for key, metadata in registry.items():
    print(f"Class: {metadata.cls.__name__}")
    print(f"Namespace: {metadata.namespace}")
    print(f"Parameters: {metadata.parameters}")
```

## Requirements

The configuration system requires:

- `tomlkit>=0.12.0` - For TOML generation with comment preservation
- `tomli>=2.0.0` (Python < 3.11) - For TOML validation

Install with:

```bash
pip install xsp-lib[schemas]
```

## Best Practices

### 1. Use Keyword-Only Parameters

Only keyword-only parameters with defaults are included:

```python
@configurable(namespace="good")
class GoodExample:
    def __init__(self, *, param: str = "default"):  # ✓ Included
        pass

@configurable(namespace="bad")
class BadExample:
    def __init__(self, param: str = "default"):  # ✗ Not included (not keyword-only)
        pass
```

### 2. Provide Clear Descriptions

```python
@configurable(
    namespace="api",
    description="REST API client configuration for external services"
)
class ApiClient:
    def __init__(self, *, base_url: str = "https://api.example.com"):
        pass
```

### 3. Use Type Hints

Type hints are displayed in generated comments:

```python
@configurable(namespace="config")
class TypedConfig:
    def __init__(
        self,
        *,
        count: int = 10,              # Type: int
        rate: float = 1.5,            # Type: float
        enabled: bool = True,         # Type: bool
        items: list[str] = (),        # Type: list
    ):
        pass
```

### 4. Organize by Namespace

Group related configurations under the same namespace:

```python
# All HTTP-related configs
@configurable(namespace="http")
class HttpTransport:
    pass

@configurable(namespace="http")
class HttpClient:
    pass

# All gRPC-related configs
@configurable(namespace="grpc")
class GrpcTransport:
    pass
```

## Limitations

### None Values

Due to tomlkit limitations, `None` values are rendered as comments rather than actual TOML entries. Users must uncomment and edit these values manually.

### Mutable Defaults

Avoid mutable defaults in configurable parameters. Use `None` as default and initialize in `__init__`:

```python
@configurable(namespace="config")
class ConfigExample:
    def __init__(
        self,
        *,
        items: list[str] | None = None,  # Use None as default
    ):
        self.items = items if items is not None else ["a", "b", "c"]
```

### Complex Types

Very complex types may not serialize well to TOML. Stick to basic types:

- Strings (`str`)
- Numbers (`int`, `float`)
- Booleans (`bool`)
- Lists/tuples of basic types
- Dictionaries with string keys

## API Reference

### @configurable

```python
def configurable(
    *,
    namespace: str,
    description: str = "",
) -> Callable[[type[T]], type[T]]:
    """
    Mark a class as configurable.
    
    Args:
        namespace: Configuration namespace (e.g., "http", "grpc")
        description: Optional description of the class
        
    Returns:
        Decorated class
    """
```

### ConfigGenerator

```python
class ConfigGenerator:
    @staticmethod
    def generate_toml(
        group_by: str = "namespace",
        validate: bool = True
    ) -> str:
        """
        Generate TOML configuration template.
        
        Args:
            group_by: How to group ("namespace" or "class")
            validate: Whether to validate generated TOML
            
        Returns:
            TOML configuration string
            
        Raises:
            ValueError: If group_by invalid or TOML invalid
        """
```

## Examples

See the [examples/](../examples/) directory for complete working examples:

- `examples/config_example.py` - Basic configuration usage
- `examples/advanced_config.py` - Advanced patterns

## See Also

- [TOML Specification](https://toml.io/)
- [tomlkit Documentation](https://github.com/sdispater/tomlkit)
