# xsp-lib: Universal AdTech Service Protocol Library

**XSP** = **X-Side Platform** (where X = DSP/SSP/any)

Comprehensive AdTech protocol repository providing:

## 🎯 Upstream Protocols
- **VAST/VPAID/VMAP** - Video ad serving templates
- **OpenRTB 2.x/3.x** - Real-time bidding
- **DAAST** - Digital audio ad serving
- **CATS** - Common AdTech Services
- Custom protocols via extensible abstractions

## 📋 Industry Standards
- **OpenDirect** - Programmatic guaranteed buying
- **AdCOM** - Advertising Common Object Model  
- **IAB Tech Lab** specifications
- XML/JSON schemas and validators

## 🚀 Infrastructure
- Pluggable transports (HTTP, gRPC, WebSocket, file, memory)
- Middleware system (retry, circuit breaker, cache, metrics, auth)
- Schema validation and documentation
- Testing utilities and fixtures

## Quick Start

```bash
pip install xsp-lib[http]
```

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
    print(result)
    
    await upstream.close()

asyncio.run(main())
```

## Architecture

### Core Abstractions

**Upstream[T]** - Generic protocol for any AdTech service:
- Fetch data from upstream services
- Health checks and resource management
- Type-safe response handling

**Transport** - Pluggable I/O layer:
- HTTP/HTTPS for REST APIs
- gRPC for binary protocols
- File/Memory for testing

**BaseUpstream** - Composition layer:
- Transport + Decoder/Encoder
- Timeout and error handling
- Default parameters and headers

### Middleware System

Chain middleware for cross-cutting concerns:
- **Retry** - Exponential backoff
- **Circuit Breaker** - Fault tolerance
- **Cache** - Response caching
- **Metrics** - Observability
- **Auth** - Authentication/authorization

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

# Development
pip install xsp-lib[dev]
```

## Examples

### Basic HTTP Upstream

```python
from xsp.core.base import BaseUpstream
from xsp.transports.http import HttpTransport

upstream = BaseUpstream(
    transport=HttpTransport(),
    decoder=lambda b: b.decode('utf-8'),
    endpoint="https://httpbin.org/get"
)

result = await upstream.fetch(params={"key": "value"})
```

### With Retry Middleware

```python
from xsp.middleware.retry import RetryMiddleware
from xsp.middleware.base import MiddlewareStack

middleware = MiddlewareStack(
    RetryMiddleware(max_attempts=3, backoff_base=2.0)
)

upstream = middleware.wrap(base_upstream)
result = await upstream.fetch()
```

### File-based Testing

```python
from xsp.transports.file import FileTransport

transport = FileTransport()
upstream = BaseUpstream(
    transport=transport,
    decoder=lambda b: b.decode('utf-8'),
    endpoint="/path/to/test/data.xml"
)
```

## Development

```bash
# Clone repository
git clone https://github.com/pv-udpv/xsp-lib.git
cd xsp-lib

# Install in development mode
pip install -e .[dev,http]

# Run tests
pytest

# Type checking
mypy src

# Linting and formatting
ruff check src tests --fix
ruff format src tests
```

## Roadmap

- [x] Core infrastructure (Issue #1)
- [ ] VAST protocol (Issue #2)
- [ ] OpenRTB protocol (Issue #3)
- [ ] DAAST protocol (Issue #4)
- [ ] CATS protocol (Issue #5)
- [ ] OpenDirect standard
- [ ] AdCOM standard
- [ ] Additional middleware (circuit breaker, cache, metrics)
- [ ] gRPC and WebSocket transports

## License

MIT - see LICENSE file for details

## GitHub Copilot Agents

This repository includes custom GitHub Copilot agents to streamline development:

- **@orchestrator** - Plans tasks and coordinates between agents
- **@developer** - Implements AdTech protocols and features
- **@tester** - Creates comprehensive test suites
- **@doc-writer** - Writes documentation and guides

See [AGENTS.md](./AGENTS.md) for detailed usage instructions.

## Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests.

## Links

- [Documentation](https://xsp-lib.readthedocs.io)
- [Issues](https://github.com/pv-udpv/xsp-lib/issues)
- [PyPI](https://pypi.org/project/xsp-lib)
