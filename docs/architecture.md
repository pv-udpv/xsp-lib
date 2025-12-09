# Architecture Overview

**xsp-lib** is built on a layered architecture with pluggable components.

## Core Abstractions

### Upstream[T]

The `Upstream[T]` protocol represents any AdTech service:

- Generic over response type `T`
- Provides `fetch()`, `close()`, and `health_check()` methods
- Protocol-agnostic interface

### Transport

The `Transport` protocol abstracts I/O operations:

- **HTTP/HTTPS** - REST APIs and XML feeds
- **gRPC** - Binary protocols
- **WebSocket** - Real-time streaming
- **File** - Testing and fixtures
- **Memory** - Unit testing

### BaseUpstream

`BaseUpstream[T]` composes transport with decoder/encoder:

```
┌─────────────────────────────────────┐
│         BaseUpstream[T]             │
├─────────────────────────────────────┤
│ - Transport (I/O)                   │
│ - Decoder (bytes → T)               │
│ - Encoder (Any → bytes)             │
│ - Default params/headers/timeout    │
└─────────────────────────────────────┘
           ↓
    ┌─────────────┐
    │  Transport  │
    └─────────────┘
```

## Middleware System

Middleware wraps upstreams for cross-cutting concerns:

```
Request → Retry → CircuitBreaker → Cache → Upstream → Response
```

Available middleware:
- **Retry** - Exponential backoff
- **Circuit Breaker** - Fault tolerance (future)
- **Cache** - Response caching (future)
- **Metrics** - Observability (future)
- **Auth** - Authentication (future)

## Protocol Implementations

Protocol-specific upstreams extend `BaseUpstream`:

- **VAST** - Video ad serving (Issue #2)
- **OpenRTB** - Real-time bidding (Issue #3)
- **DAAST** - Digital audio ads (Issue #4)
- **CATS** - Common AdTech services (Issue #5)

## Design Principles

1. **Composability** - Small, focused components
2. **Type Safety** - Full type hints and strict mypy
3. **Testability** - Pluggable transports for easy testing
4. **Extensibility** - Protocol-based design
5. **Production Ready** - Error handling, timeouts, retries

## Directory Structure

```
src/xsp/
├── core/           # Core abstractions
├── transports/     # Transport implementations
├── middleware/     # Middleware system
├── protocols/      # Protocol implementations
├── standards/      # Industry standards
├── schemas/        # Validation and schemas
└── utils/          # Utilities
```
