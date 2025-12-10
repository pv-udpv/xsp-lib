# Protocol-Agnostic Design

This document describes xsp-lib's protocol-agnostic design principles, focusing on TypedDict schemas and extensibility patterns for supporting multiple AdTech protocols (VAST, OpenRTB, DAAST, CATS).

## Design Philosophy

xsp-lib is built to support **any** AdTech protocol without requiring changes to core abstractions. This is achieved through:

1. **TypedDict Schemas** - Protocol data as plain dictionaries with type hints
2. **Generic Upstream[T]** - Upstream services parameterized by response type
3. **Pluggable Transports** - I/O layer independent of protocol
4. **Encoder/Decoder Pattern** - Separate serialization from business logic
5. **Protocol Extensions** - Add new protocols without modifying core

## Core Principles

### 1. Separation of Concerns

```
┌─────────────────────────────────────────────────────────────┐
│                   Protocol Layer                            │
│  (VAST, OpenRTB, DAAST - protocol-specific logic)          │
│  • Schema definitions (TypedDict)                           │
│  • Macro substitution                                       │
│  • Validation rules                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Core Layer                                │
│  (Protocol-agnostic abstractions)                           │
│  • Upstream[T] protocol                                     │
│  • BaseUpstream[T] implementation                           │
│  • Transport abstraction                                    │
│  • SessionContext                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Transport Layer                           │
│  (Protocol-agnostic I/O)                                    │
│  • HttpTransport                                            │
│  • GrpcTransport                                            │
│  • FileTransport                                            │
└─────────────────────────────────────────────────────────────┘
```

### 2. Type Safety with TypedDict

**Why TypedDict?**
- ✅ Preserves protocol structure (maps to JSON/XML schemas)
- ✅ Type checking without runtime overhead
- ✅ Easy serialization (dict → JSON/XML)
- ✅ Compatible with mypy --strict
- ❌ **NO** Pydantic models at protocol layer (adds overhead)
- ❌ **NO** Dataclasses (less flexible for nested structures)

**Example - VAST Schema:**

```python
from typing import TypedDict, Required, NotRequired

class VastCreative(TypedDict):
    """VAST Creative schema per IAB VAST 4.2 §2.3.2."""
    
    id: Required[str]
    sequence: NotRequired[int]
    ad_id: NotRequired[str]
    api_framework: NotRequired[str]

class VastLinear(TypedDict):
    """VAST Linear creative per IAB VAST 4.2 §2.3.3."""
    
    duration: Required[int]  # Seconds
    media_files: Required[list["VastMediaFile"]]
    video_clicks: NotRequired["VastVideoClicks"]
    tracking_events: NotRequired[list["VastTracking"]]
    ad_parameters: NotRequired[str]
    skip_offset: NotRequired[int]

class VastMediaFile(TypedDict):
    """VAST MediaFile per IAB VAST 4.2 §2.3.3.3."""
    
    url: Required[str]
    delivery: Required[str]  # "progressive" | "streaming"
    type: Required[str]  # MIME type
    width: NotRequired[int]
    height: NotRequired[int]
    codec: NotRequired[str]
    bitrate: NotRequired[int]
    min_bitrate: NotRequired[int]
    max_bitrate: NotRequired[int]
    scalable: NotRequired[bool]
    maintain_aspect_ratio: NotRequired[bool]
    api_framework: NotRequired[str]

class VastInlineAd(TypedDict):
    """VAST InLine ad per IAB VAST 4.2 §2.3.2."""
    
    ad_system: Required[str]
    ad_title: Required[str]
    creatives: Required[list[VastCreative]]
    description: NotRequired[str]
    advertiser: NotRequired[str]
    pricing: NotRequired[str]
    survey: NotRequired[str]
    error_url: NotRequired[str]
    impression_urls: NotRequired[list[str]]
    extensions: NotRequired[dict[str, Any]]
```

**Example - OpenRTB Schema:**

```python
class BidRequest(TypedDict):
    """OpenRTB 2.6 Bid Request per §3.2.1."""
    
    id: Required[str]
    imp: Required[list["Impression"]]
    site: NotRequired["Site"]
    app: NotRequired["App"]
    device: NotRequired["Device"]
    user: NotRequired["User"]
    test: NotRequired[int]
    at: NotRequired[int]  # Auction type
    tmax: NotRequired[int]  # Max timeout in ms
    wseat: NotRequired[list[str]]  # Whitelist of buyer seats
    bseat: NotRequired[list[str]]  # Blacklist of buyer seats
    allimps: NotRequired[int]
    cur: NotRequired[list[str]]  # Currencies
    wlang: NotRequired[list[str]]  # Whitelist of languages
    bcat: NotRequired[list[str]]  # Blocked advertiser categories
    badv: NotRequired[list[str]]  # Blocked advertiser domains
    bapp: NotRequired[list[str]]  # Blocked app bundle IDs
    source: NotRequired["Source"]
    regs: NotRequired["Regs"]
    ext: NotRequired[dict[str, Any]]

class Impression(TypedDict):
    """OpenRTB 2.6 Impression per §3.2.4."""
    
    id: Required[str]
    banner: NotRequired["Banner"]
    video: NotRequired["Video"]
    audio: NotRequired["Audio"]
    native: NotRequired["Native"]
    pmp: NotRequired["PMP"]
    displaymanager: NotRequired[str]
    displaymanagerver: NotRequired[str]
    instl: NotRequired[int]
    tagid: NotRequired[str]
    bidfloor: NotRequired[float]
    bidfloorcur: NotRequired[str]
    secure: NotRequired[int]
    iframebuster: NotRequired[list[str]]
    exp: NotRequired[int]
    ext: NotRequired[dict[str, Any]]

class BidResponse(TypedDict):
    """OpenRTB 2.6 Bid Response per §3.2.2."""
    
    id: Required[str]
    seatbid: NotRequired[list["SeatBid"]]
    bidid: NotRequired[str]
    cur: NotRequired[str]
    customdata: NotRequired[str]
    nbr: NotRequired[int]  # No-bid reason code
    ext: NotRequired[dict[str, Any]]
```

### 3. Generic Upstream[T]

The `Upstream[T]` protocol is generic over response type `T`:

```python
from typing import Protocol, TypeVar, Any

T = TypeVar("T", covariant=True)

class Upstream(Protocol[T]):
    """Universal upstream service protocol."""
    
    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> T:
        """Fetch data from upstream."""
        ...
```

**Protocol-Specific Instantiations:**

```python
# VAST upstream returns VastInlineAd
VastUpstream: Upstream[VastInlineAd]

# OpenRTB upstream returns BidResponse
OpenRtbUpstream: Upstream[BidResponse]

# Custom protocol upstream
CustomUpstream: Upstream[CustomResponse]
```

### 4. Encoder/Decoder Pattern

Separate serialization logic from business logic:

```python
from typing import Callable, Any

class BaseUpstream(Generic[T]):
    """Base upstream with encoder/decoder composition."""
    
    def __init__(
        self,
        transport: Transport,
        decoder: Callable[[bytes], T],
        encoder: Callable[[Any], bytes] | None = None,
        config: UpstreamConfig | None = None,
    ):
        self._transport = transport
        self._decoder = decoder
        self._encoder = encoder or self._default_encoder
        self._config = config or UpstreamConfig()
    
    async def fetch(
        self,
        *,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> T:
        # Encode request
        request_bytes = self._encoder(params)
        
        # Send via transport
        response_bytes = await self._transport.send(
            data=request_bytes,
            url=self._config.endpoint,
            timeout=self._config.timeout,
        )
        
        # Decode response
        return self._decoder(response_bytes)
```

**Protocol-Specific Encoders/Decoders:**

```python
import json
import xml.etree.ElementTree as ET

# VAST decoder (XML → VastInlineAd)
def decode_vast_xml(data: bytes) -> VastInlineAd:
    """Decode VAST XML to TypedDict per IAB VAST 4.2."""
    root = ET.fromstring(data)
    # Parse XML and construct VastInlineAd TypedDict
    return VastInlineAd(
        ad_system=root.find(".//AdSystem").text,
        ad_title=root.find(".//AdTitle").text,
        creatives=[...],
    )

# OpenRTB encoder (BidRequest → JSON bytes)
def encode_openrtb_request(bid_request: BidRequest) -> bytes:
    """Encode OpenRTB bid request to JSON per OpenRTB 2.6 §3.2.1."""
    return json.dumps(bid_request).encode("utf-8")

# OpenRTB decoder (JSON bytes → BidResponse)
def decode_openrtb_response(data: bytes) -> BidResponse:
    """Decode OpenRTB bid response from JSON per OpenRTB 2.6 §3.2.2."""
    return json.loads(data)
```

**Usage:**

```python
# VAST upstream
vast_upstream = BaseUpstream[VastInlineAd](
    transport=http_transport,
    decoder=decode_vast_xml,
    config=UpstreamConfig(endpoint="https://ads.example.com/vast"),
)

# OpenRTB upstream
openrtb_upstream = BaseUpstream[BidResponse](
    transport=http_transport,
    encoder=encode_openrtb_request,
    decoder=decode_openrtb_response,
    config=UpstreamConfig(endpoint="https://bidder.example.com/openrtb"),
)
```

## Adding New Protocols

### Step 1: Define TypedDict Schemas

```python
# src/xsp/protocols/my_protocol/types.py

from typing import TypedDict, Required, NotRequired

class MyProtocolRequest(TypedDict):
    """My custom protocol request schema."""
    
    id: Required[str]
    timestamp: Required[int]
    data: NotRequired[dict[str, Any]]

class MyProtocolResponse(TypedDict):
    """My custom protocol response schema."""
    
    id: Required[str]
    status: Required[str]
    result: NotRequired[Any]
```

### Step 2: Implement Encoder/Decoder

```python
# src/xsp/protocols/my_protocol/codec.py

import json

def encode_my_protocol_request(request: MyProtocolRequest) -> bytes:
    """Encode request to JSON."""
    return json.dumps(request).encode("utf-8")

def decode_my_protocol_response(data: bytes) -> MyProtocolResponse:
    """Decode response from JSON."""
    return json.loads(data)
```

### Step 3: Create Protocol-Specific Upstream

```python
# src/xsp/protocols/my_protocol/upstream.py

from xsp.core.base import BaseUpstream
from xsp.core.transport import Transport
from xsp.core.config import UpstreamConfig
from .types import MyProtocolRequest, MyProtocolResponse
from .codec import encode_my_protocol_request, decode_my_protocol_response

class MyProtocolUpstream(BaseUpstream[MyProtocolResponse]):
    """My custom protocol upstream."""
    
    def __init__(
        self,
        transport: Transport,
        config: UpstreamConfig | None = None,
    ):
        super().__init__(
            transport=transport,
            encoder=encode_my_protocol_request,
            decoder=decode_my_protocol_response,
            config=config,
        )
    
    async def fetch(
        self,
        request: MyProtocolRequest,
        **kwargs: Any,
    ) -> MyProtocolResponse:
        """Fetch response from my protocol upstream."""
        return await super().fetch(params=request, **kwargs)
```

### Step 4: Use the New Protocol

```python
from xsp.transports.http import HttpTransport
from xsp.protocols.my_protocol import MyProtocolUpstream, MyProtocolRequest

# Create transport
transport = HttpTransport()

# Create upstream
upstream = MyProtocolUpstream(
    transport=transport,
    config=UpstreamConfig(endpoint="https://api.example.com/my-protocol"),
)

# Make request
request = MyProtocolRequest(id="req-123", timestamp=1702224000000)
response = await upstream.fetch(request)
```

## Protocol Extensions

### Extending VAST for Custom Fields

VAST allows extensions via `<Extensions>` element:

```python
class VastExtension(TypedDict):
    """VAST Extension per IAB VAST 4.2 §2.3.4.4."""
    
    type: NotRequired[str]
    data: NotRequired[dict[str, Any]]

class VastInlineAdWithExtensions(VastInlineAd):
    """Extended VAST InLine ad with custom fields."""
    
    extensions: NotRequired[list[VastExtension]]

# Custom extension decoder
def decode_vast_with_extensions(data: bytes) -> VastInlineAdWithExtensions:
    """Decode VAST XML with custom extensions."""
    root = ET.fromstring(data)
    
    # Standard VAST parsing
    ad = decode_vast_xml(data)
    
    # Parse extensions
    extensions = []
    for ext_elem in root.findall(".//Extension"):
        extensions.append(VastExtension(
            type=ext_elem.get("type"),
            data=json.loads(ext_elem.text or "{}"),
        ))
    
    ad["extensions"] = extensions
    return ad
```

### Extending OpenRTB with Custom Objects

OpenRTB allows extensions via `ext` field:

```python
class BidRequestWithCustomExt(BidRequest):
    """OpenRTB bid request with custom extension."""
    
    ext: NotRequired[dict[str, Any]]

# Usage
bid_request = BidRequestWithCustomExt(
    id="bid-123",
    imp=[...],
    ext={
        "my_custom_field": "value",
        "my_custom_object": {"nested": "data"},
    },
)
```

## Validation Strategies

### 1. Runtime Validation (Optional)

Use TypedDict with runtime checking for critical paths:

```python
from typing import get_type_hints
from typing_extensions import TypedDict

def validate_typed_dict(obj: dict, schema: type[TypedDict]) -> None:
    """Validate dict against TypedDict schema at runtime."""
    hints = get_type_hints(schema)
    required = getattr(schema, "__required_keys__", set())
    
    # Check required keys
    for key in required:
        if key not in obj:
            raise ValueError(f"Missing required key: {key}")
    
    # Type checking (simplified)
    for key, value in obj.items():
        if key in hints:
            expected_type = hints[key]
            # Perform type checking...
```

### 2. Static Validation (Recommended)

Use mypy for static type checking:

```bash
# Run mypy with strict mode
mypy --strict src/
```

### 3. Schema Validation (For Critical Systems)

Use JSON Schema for runtime validation:

```python
import jsonschema

# Define JSON schema
VAST_SCHEMA = {
    "type": "object",
    "required": ["ad_system", "ad_title", "creatives"],
    "properties": {
        "ad_system": {"type": "string"},
        "ad_title": {"type": "string"},
        "creatives": {"type": "array"},
    },
}

def validate_vast_response(response: VastInlineAd) -> None:
    """Validate VAST response against JSON schema."""
    jsonschema.validate(instance=response, schema=VAST_SCHEMA)
```

## Performance Considerations

### TypedDict vs. Dataclass vs. Pydantic

| Approach | Pros | Cons | Use Case |
|----------|------|------|----------|
| **TypedDict** | Zero runtime overhead, preserves dict structure | No validation, no default values | Protocol schemas (VAST, OpenRTB) |
| **Dataclass** | Type safety, default values | Conversion overhead (dict ↔ class) | Internal models |
| **Pydantic** | Validation, serialization | Runtime overhead, complexity | API boundaries, config |

**Recommendation:**
- ✅ TypedDict for protocol schemas (VAST, OpenRTB)
- ✅ Dataclass for internal models (SessionContext, UpstreamConfig)
- ✅ Pydantic for configuration (XspSettings)
- ❌ Avoid Pydantic for high-throughput protocol parsing

### Encoder/Decoder Performance

```python
import orjson  # Faster JSON library

# Use orjson for OpenRTB (10x faster than json)
def encode_openrtb_request(bid_request: BidRequest) -> bytes:
    """Encode with orjson for performance."""
    return orjson.dumps(bid_request)

def decode_openrtb_response(data: bytes) -> BidResponse:
    """Decode with orjson for performance."""
    return orjson.loads(data)
```

### Caching Decoded Responses

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def decode_vast_xml_cached(data: bytes) -> VastInlineAd:
    """Cached VAST XML decoder for repeated responses."""
    return decode_vast_xml(data)
```

## Testing Protocol-Agnostic Code

### Unit Tests with Multiple Protocols

```python
import pytest
from xsp.protocols.vast import VastUpstream, VastInlineAd
from xsp.protocols.openrtb import OpenRtbUpstream, BidResponse

@pytest.mark.parametrize("upstream_class,response_type", [
    (VastUpstream, VastInlineAd),
    (OpenRtbUpstream, BidResponse),
])
@pytest.mark.asyncio
async def test_upstream_generic(upstream_class, response_type):
    """Test that all upstreams satisfy Upstream[T] protocol."""
    transport = MemoryTransport(fixture_data=b"{}")
    upstream = upstream_class(transport=transport)
    
    # All upstreams must implement fetch()
    response = await upstream.fetch()
    
    # Response type must match
    assert isinstance(response, dict)  # TypedDict is dict at runtime
```

### Fixture Data for Protocols

```python
# tests/fixtures/vast/inline_ad.xml
VAST_INLINE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
  <Ad id="12345">
    <InLine>
      <AdSystem>ExampleAdSystem</AdSystem>
      <AdTitle>Example Ad</AdTitle>
      <Creatives>
        <Creative id="creative1">
          <Linear>
            <Duration>00:00:30</Duration>
            <MediaFiles>
              <MediaFile delivery="progressive" type="video/mp4">
                https://example.com/video.mp4
              </MediaFile>
            </MediaFiles>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>
"""

# tests/fixtures/openrtb/bid_response.json
BID_RESPONSE_JSON = b"""{
  "id": "bid-123",
  "seatbid": [
    {
      "bid": [
        {
          "id": "1",
          "impid": "imp-1",
          "price": 2.50,
          "adm": "<creative>...</creative>",
          "crid": "creative-123"
        }
      ]
    }
  ],
  "cur": "USD"
}
"""
```

## Best Practices

1. **Use TypedDict for protocol schemas** - Preserves dict structure, zero overhead
2. **Use Required/NotRequired** - Explicitly mark required fields
3. **Document IAB spec references** - Link to spec sections in docstrings
4. **Separate encoder/decoder logic** - Keep serialization independent
5. **Validate at boundaries** - Use JSON Schema for external data
6. **Cache decoded responses** - Use LRU cache for repeated responses
7. **Use fast JSON libraries** - orjson for high-throughput protocols
8. **Test with real fixtures** - Use IAB example payloads

## Migration from Other Approaches

### From Pydantic Models

**Before:**
```python
from pydantic import BaseModel

class VastAd(BaseModel):
    ad_system: str
    ad_title: str
    creatives: list[dict]
```

**After:**
```python
from typing import TypedDict, Required

class VastInlineAd(TypedDict):
    """VAST InLine ad per IAB VAST 4.2 §2.3.2."""
    
    ad_system: Required[str]
    ad_title: Required[str]
    creatives: Required[list[dict]]
```

### From Dataclasses

**Before:**
```python
from dataclasses import dataclass

@dataclass
class BidResponse:
    id: str
    seatbid: list[dict] | None = None
```

**After:**
```python
from typing import TypedDict, Required, NotRequired

class BidResponse(TypedDict):
    """OpenRTB 2.6 Bid Response per §3.2.2."""
    
    id: Required[str]
    seatbid: NotRequired[list["SeatBid"]]
```

## References

- [PEP 589 - TypedDict](https://peps.python.org/pep-0589/) - TypedDict specification
- [PEP 655 - Required and NotRequired](https://peps.python.org/pep-0655/) - Marking required fields
- [IAB VAST 4.2 Specification](https://iabtechlab.com/standards/vast/) - VAST schema reference
- [IAB OpenRTB 2.6 Specification](https://iabtechlab.com/standards/openrtb/) - OpenRTB schema reference
- [mypy Type Checking](https://mypy.readthedocs.io/) - Static type checking

## Related Documentation

- [Final Architecture](./final-architecture.md) - Complete system design
- [Session Management](./session-management.md) - SessionContext and UpstreamSession
- [Terminology Guide](./terminology.md) - Correct terminology
