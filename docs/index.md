# xsp-lib Documentation

Welcome to the **xsp-lib** documentation - the universal AdTech service protocol library.

## Overview

**xsp-lib** provides a comprehensive set of tools for working with AdTech protocols and standards:

- **Upstream Protocols**: VAST, OpenRTB, DAAST, CATS
- **Industry Standards**: OpenDirect, AdCOM, IAB specifications
- **Infrastructure**: Pluggable transports, middleware system, testing utilities

## Quick Links

- [Quick Start Guide](quickstart.md)
- [Architecture Overview](architecture.md)
- [Configuration Guide](configuration.md)
- [Protocol Documentation](protocols/)
- [Standards Documentation (AdCOM)](adcom.md)

### Architecture Documentation

- [Final Architecture](architecture/final-architecture.md) - Complete system design
- [Session Management](architecture/session-management.md) - Session lifecycle and patterns
- [Terminology Guide](architecture/terminology.md) - Correct terminology (dial/request/resolve/serve)
- [Protocol-Agnostic Design](architecture/protocol-agnostic-design.md) - TypedDict schemas and extensions

### Guides

- [Session Management Guide](guides/session-management.md) - Practical session examples
- [Stateful Ad Serving](guides/stateful-ad-serving.md) - Frequency capping and budget tracking

## Installation

```bash
# Core library
pip install xsp-lib

# With HTTP transport
pip install xsp-lib[http]

# With specific protocols
pip install xsp-lib[vast,openrtb]

# Full installation
pip install xsp-lib[all]
```

## Basic Usage

```python
import asyncio
from xsp.core.base import BaseUpstream
from xsp.transports.http import HttpTransport

async def main():
    upstream = BaseUpstream(
        transport=HttpTransport(),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="https://api.example.com/data"
    )
    
    result = await upstream.fetch()
    await upstream.close()

asyncio.run(main())
```

## Getting Help

- [GitHub Issues](https://github.com/pv-udpv/xsp-lib/issues)
- [Discussions](https://github.com/pv-udpv/xsp-lib/discussions)
