# VAST Parser - Version-Aware XML Parsing

## Overview

The VAST parser in xsp-lib provides version-aware XML parsing that automatically filters elements based on VAST version compatibility.

## Features

- **Multi-version support**: VAST 2.0, 3.0, 4.0, 4.1, 4.2
- **Automatic filtering**: Parse only version-compatible elements
- **Strict mode**: Validate XML version matches parser version
- **Custom elements**: Register provider-specific extensions
- **Backward compatibility**: Parse newer VAST with older parser versions

## Basic Usage

### Parse VAST 4.2 XML

```python
from xsp.protocols.vast import VastParser, VastVersion

# Create parser for VAST 4.2
parser = VastParser(version=VastVersion.V4_2)

# Parse XML - includes all elements up to 4.2
vast_data = parser.parse_vast(xml_string)

print(vast_data["ad_system"])  # Core element
print(vast_data["universal_ad_id"])  # VAST 3.0+ element
print(vast_data["mezzanine"])  # VAST 4.0+ element
print(vast_data["blocked_ad_categories"])  # VAST 4.2+ element
```

### Parse with VAST 3.0 Parser

```python
# Create parser for VAST 3.0
parser_v3 = VastParser(version=VastVersion.V3_0)

# Parse same XML - automatically filters out 4.x elements
vast_data = parser_v3.parse_vast(xml_string)

print(vast_data["ad_system"])  # ✓ Present (2.0+)
print(vast_data["universal_ad_id"])  # ✓ Present (3.0+)
print(vast_data.get("mezzanine"))  # ✗ None (4.0+, not compatible)
print(vast_data.get("blocked_ad_categories"))  # ✗ None (4.2+, not compatible)
```

## Version Filtering

### Element Registry

The parser maintains a registry of VAST elements tagged with version info:

```python
from xsp.protocols.vast.parser import ElementDefinition

# Example registry entries
ELEMENT_REGISTRY = {
    # Core elements (all versions)
    "ad_system": ElementDefinition(
        xpath=".//AdSystem",
        introduced=VastVersion.V2_0,
    ),
    
    # VAST 3.0+ elements
    "universal_ad_id": ElementDefinition(
        xpath=".//UniversalAdId",
        introduced=VastVersion.V3_0,
    ),
    
    # VAST 4.0+ elements
    "mezzanine": ElementDefinition(
        xpath=".//Mezzanine",
        introduced=VastVersion.V4_0,
    ),
    
    # VAST 4.2+ elements
    "blocked_ad_categories": ElementDefinition(
        xpath=".//BlockedAdCategories",
        introduced=VastVersion.V4_2,
    ),
}
```

### Compatibility Rules

An element is parsed only if:
1. It was introduced in current or earlier VAST version
2. It has not been deprecated in current VAST version

```python
# Parser version: 4.0
parser = VastParser(version=VastVersion.V4_0)

# ✓ Parsed: introduced in 3.0, compatible with 4.0
"universal_ad_id" -> included

# ✗ Skipped: introduced in 4.2, not yet available in 4.0
"blocked_ad_categories" -> excluded

# ✗ Skipped: deprecated in 4.0
"deprecated_element" -> excluded
```

## Strict Mode

Validate that XML version matches parser version:

```python
# Create strict parser for VAST 4.2
parser = VastParser(version=VastVersion.V4_2, strict=True)

# ✓ OK: XML version matches parser version
xml_42 = '<VAST version="4.2">...</VAST>'
result = parser.parse_vast(xml_42)

# ✗ Error: XML version 3.0 does not match parser version 4.2
xml_30 = '<VAST version="3.0">...</VAST>'
parser.parse_vast(xml_30)  # Raises ValueError
```

## Custom Elements

Register provider-specific or custom elements:

```python
parser = VastParser(version=VastVersion.V4_2)

# Register custom element
parser.register_element(
    name="custom_tracking",
    xpath=".//CustomTracking",
    introduced=VastVersion.V3_0,
    parser_func=lambda el: {
        "url": el.get("url"),
        "type": el.get("type"),
        "event": el.text,
    },
)

# Parse XML with custom element
vast_data = parser.parse_vast(xml_with_custom)
print(vast_data["custom_tracking"])  # {"url": "...", "type": "...", "event": "..."}
```

## Integration with VastUpstream

Use parser with upstream for end-to-end flow:

```python
from xsp.transports.http import HttpTransport
from xsp.protocols.vast import VastUpstream, VastParser, VastVersion

# Create upstream and parser with same version
transport = HttpTransport()
upstream = VastUpstream(
    transport=transport,
    endpoint="https://ads.example.com/vast",
    version=VastVersion.V3_0,
)
parser = VastParser(version=VastVersion.V3_0)

# Fetch and parse with consistent versioning
xml = await upstream.fetch(params={"uid": "123"})
vast_data = parser.parse_vast(xml)

# vast_data contains only VAST 3.0-compatible elements
```

## Backward Compatibility

### Scenario: Receive VAST 4.2, Parse as 3.0

This pattern ensures old code continues working when ad servers upgrade:

```python
# Your code is configured for VAST 3.0
parser = VastParser(version=VastVersion.V3_0)

# Ad server sends VAST 4.2 XML
xml_from_server = '<VAST version="4.2">...</VAST>'

# Parser extracts only 3.0-compatible elements
vast_data = parser.parse_vast(xml_from_server)

# Your existing code that expects 3.0 data continues to work
print(vast_data["ad_system"])  # ✓ Works
print(vast_data["universal_ad_id"])  # ✓ Works (3.0+)
print(vast_data.get("mezzanine"))  # None (4.0+, ignored)

# No breaking changes, no refactoring needed
```

## Version Metadata

Parsed data includes version information:

```python
vast_data = parser.parse_vast(xml)

print(vast_data["version"])  # "4.2" (from XML)
print(vast_data["_parser_version"])  # "3.0" (parser config)

# Detect version mismatches programmatically
if vast_data["version"] != vast_data["_parser_version"]:
    print(f"Warning: parsing {vast_data['version']} as {vast_data['_parser_version']}")
```

## Element List by Version

### VAST 2.0 (Base)
- AdSystem
- AdTitle
- Description
- Advertiser
- Survey
- Error
- Impression

### VAST 3.0 Additions
- UniversalAdId
- AdVerifications
- Pricing

### VAST 4.0 Additions
- Mezzanine
- Category

### VAST 4.1 Additions
- AdChoices

### VAST 4.2 Additions
- BlockedAdCategories

## Best Practices

### 1. Match Parser and Upstream Versions

```python
# ✓ Good: consistent versioning
upstream = VastUpstream(version=VastVersion.V3_0)
parser = VastParser(version=VastVersion.V3_0)

# ✗ Bad: version mismatch
upstream = VastUpstream(version=VastVersion.V4_2)
parser = VastParser(version=VastVersion.V3_0)  # Inconsistent
```

### 2. Use Strict Mode in Tests

```python
# Test that your XML fixtures match expected version
parser = VastParser(version=VastVersion.V4_2, strict=True)
vast_data = parser.parse_vast(fixture_xml)  # Raises if version != 4.2
```

### 3. Graceful Degradation

```python
# Parse with lower version for maximum compatibility
parser = VastParser(version=VastVersion.V3_0)

# Access optional 4.x elements safely
mezzanine = vast_data.get("mezzanine")  # None if not present
if mezzanine:
    # Use high-quality source if available
    use_mezzanine(mezzanine)
else:
    # Fallback to standard MediaFile
    use_media_file(vast_data["media_files"][0])
```

## Error Handling

```python
from xml.etree.ElementTree import ParseError

try:
    vast_data = parser.parse_vast(xml_string)
except ParseError as e:
    # Malformed XML
    print(f"Invalid XML: {e}")
except ValueError as e:
    # Strict mode version mismatch
    print(f"Version error: {e}")
```
