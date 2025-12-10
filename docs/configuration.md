# Configuration System

## Overview

The xsp-lib configuration system uses the `@configurable` decorator to mark classes whose parameters should be exposed in configuration files. This provides explicit control over what settings are configurable and enables automatic configuration template generation.

## @configurable Decorator

The `@configurable` decorator marks classes whose parameters should be exposed in configuration files.

### Usage

```python
from xsp.core.configurable import configurable

@configurable(
    namespace="vast",
    description="VAST protocol settings"
)
class VastUpstream:
    def __init__(
        self,
        transport: Transport,  # Required positional arg (not in config)
        endpoint: str,         # Required positional arg (not in config)
        *,
        version: VastVersion = VastVersion.V4_2,  # Configurable
        enable_macros: bool = True,                # Configurable
    ):
        ...
```

### Parameters

- **namespace** (optional): Configuration namespace (e.g., "vast", "openrtb"). Defaults to module name if not provided.
- **description** (optional): Human-readable description for documentation.

### Behavior

The decorator extracts **keyword-only parameters with defaults** from the class `__init__` method. Required positional arguments (like `transport` and `endpoint`) are excluded from configuration.

Parameter descriptions are automatically extracted from the docstring if available:

```python
@configurable(namespace="vast")
class VastUpstream:
    def __init__(
        self,
        transport: Transport,
        endpoint: str,
        *,
        timeout: float = 30.0,
    ):
        """
        Initialize VAST upstream.

        Args:
            transport: Transport implementation
            endpoint: VAST ad server URL
            timeout: Request timeout in seconds
        """
```

The description "Request timeout in seconds" will be included in generated configuration templates.

## Generating Configuration Templates

### Command-Line Tool

Generate configuration templates using the `xsp-generate-config` command:

```bash
# Generate TOML template to stdout
xsp-generate-config

# Save to file
xsp-generate-config --output settings.toml

# Use class-based grouping instead of namespace
xsp-generate-config --group-by class
```

### Python Module

You can also run the tool as a Python module:

```bash
python -m xsp.cli.generate_config --format toml
```

### Example Output

```toml
# XSP-lib Configuration Template
# Auto-generated from @configurable registry
#
# This file contains all configurable parameters from xsp-lib.
# Uncomment and modify values as needed.

[vast]
# VAST protocol upstream for video ad serving
# Source: VastUpstream

# Expected VAST version
# Type: VastVersion
version = "4.2"

# Enable IAB macro substitution
# Type: bool
enable_macros = true

# Validate XML structure after fetch
# Type: bool
validate_xml = false
```

## Programmatic Access

### Registry Access

Access the configurable registry programmatically:

```python
from xsp.core.configurable import get_configurable_registry, get_configurable_by_namespace

# Get all registered configurables
registry = get_configurable_registry()

# Get configurables for a specific namespace
vast_configs = get_configurable_by_namespace("vast")

for metadata in vast_configs:
    print(f"Class: {metadata.cls.__name__}")
    print(f"Namespace: {metadata.namespace}")
    print(f"Description: {metadata.description}")
    for param_name, param_info in metadata.parameters.items():
        print(f"  - {param_name}: {param_info.type}, default={param_info.default}")
```

### Template Generation

Generate templates programmatically:

```python
from xsp.core.config_generator import ConfigGenerator

# Generate TOML
toml_config = ConfigGenerator.generate_toml(group_by="namespace")

# Write to file
with open("settings.toml", "w") as f:
    f.write(toml_config)
```

## Grouping Strategies

### Namespace Grouping (Default)

Groups configuration by namespace:

```toml
[vast]
version = "4.2"
enable_macros = true

[openrtb]
timeout = 30.0
```

### Class Grouping

Groups configuration by class name (lowercased):

```toml
[vastupstream]
version = "4.2"
enable_macros = true

[openrtbbidder]
timeout = 30.0
```

## Type Safety

The configuration system maintains strict type safety:

- All code passes `mypy --strict` type checking
- Parameter types are preserved from `__init__` signatures
- Type hints are included in generated templates as comments

## Future Enhancements

The following features are planned for future releases:

- YAML/JSON template generation (currently TOML only)
- Configuration file validation using pydantic-settings
- Multi-file config merging
- Environment-specific configurations (development/staging/production)
- Configuration priority resolution (env vars → files → defaults)

## Best Practices

1. **Only decorate classes with configurable parameters**: Don't use `@configurable` on classes without keyword-only defaults.

2. **Use meaningful namespaces**: Group related configuration under logical namespaces (e.g., "vast", "openrtb").

3. **Write descriptive docstrings**: Parameter descriptions in docstrings are automatically included in configuration templates.

4. **Use keyword-only parameters**: Only parameters after `*` in the signature are configurable. This prevents required dependencies from appearing in config files.

5. **Provide sensible defaults**: All configurable parameters should have defaults that work for common use cases.

## Example: Multiple Configurables

```python
from xsp.core.configurable import configurable

@configurable(
    namespace="vast",
    description="VAST protocol upstream for video ad serving"
)
class VastUpstream:
    def __init__(
        self,
        transport: Transport,
        endpoint: str,
        *,
        version: VastVersion = VastVersion.V4_2,
        enable_macros: bool = True,
        validate_xml: bool = False,
    ):
        """
        Initialize VAST upstream.

        Args:
            transport: Transport implementation
            endpoint: VAST ad server URL
            version: Expected VAST version
            enable_macros: Enable IAB macro substitution
            validate_xml: Validate XML structure after fetch
        """
        ...

@configurable(
    namespace="http",
    description="HTTP transport configuration"
)
class HttpTransport:
    def __init__(
        self,
        *,
        timeout: float = 30.0,
        max_redirects: int = 5,
        verify_ssl: bool = True,
    ):
        """
        Initialize HTTP transport.

        Args:
            timeout: Request timeout in seconds
            max_redirects: Maximum number of redirects to follow
            verify_ssl: Verify SSL certificates
        """
        ...
```

Generated configuration:

```toml
[http]
# HTTP transport configuration
# Source: HttpTransport

# Request timeout in seconds
# Type: float
timeout = 30.0

# Maximum number of redirects to follow
# Type: int
max_redirects = 5

# Verify SSL certificates
# Type: bool
verify_ssl = true


[vast]
# VAST protocol upstream for video ad serving
# Source: VastUpstream

# Expected VAST version
# Type: VastVersion
version = "4.2"

# Enable IAB macro substitution
# Type: bool
enable_macros = true

# Validate XML structure after fetch
# Type: bool
validate_xml = false
```
