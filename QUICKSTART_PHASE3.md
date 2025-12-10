# Quick Start: Phase 3 Orchestrator

## Installation

```bash
pip install -e .[http]
```

## Basic Usage

```python
import asyncio
from xsp import AdRequest, Orchestrator
from xsp.protocols.vast import ChainResolver, VastProtocolHandler, VastUpstream
from xsp.transports.http import HttpTransport

async def main():
    # Setup VAST protocol handler
    transport = HttpTransport()
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast"
    )
    resolver = ChainResolver(upstream=upstream)
    handler = VastProtocolHandler(chain_resolver=resolver)
    
    # Create orchestrator
    orchestrator = Orchestrator(handlers={"vast": handler})
    
    # Serve ad request
    request = AdRequest(
        protocol="vast",
        user_id="user123",
        ip_address="192.168.1.1",
    )
    
    response = await orchestrator.serve(request)
    print(f"Status: {response.status}")
    print(f"VAST XML length: {len(response.data)} bytes")
    
    await orchestrator.close()

asyncio.run(main())
```

## With Caching

```python
from xsp import InMemoryStateBackend

cache_backend = InMemoryStateBackend()

orchestrator = Orchestrator(
    handlers={"vast": handler},
    cache_backend=cache_backend,
    enable_caching=True,
    cache_ttl=300.0,  # 5 minutes
)
```

## With Redis Caching

```python
import redis.asyncio as redis
from xsp.core.state import RedisStateBackend

# Create Redis client
redis_client = await redis.from_url("redis://localhost:6379")
cache_backend = RedisStateBackend(redis_client)

orchestrator = Orchestrator(
    handlers={"vast": handler},
    cache_backend=cache_backend,
    enable_caching=True,
    cache_ttl=300.0,
)
```

## Complete Example

See `examples/orchestrator_example.py` for a complete working example with:
- Multiple request types
- Caching demonstration
- Error handling
- Auto-protocol detection

## Run Tests

```bash
# All Phase 3 tests
pytest tests/unit/core/test_state.py -v
pytest tests/unit/protocols/test_vast_chain_resolver.py -v
pytest tests/unit/protocols/test_vast_handler.py -v
pytest tests/unit/test_orchestrator.py -v
pytest tests/integration/test_orchestration_workflow.py -v

# All tests
pytest tests/ --ignore=tests/unit/standards --ignore=tests/unit/test_core_config.py
```

## Documentation

- **Full Documentation**: `docs/phase3-advanced-features.md`
- **Completion Summary**: `PHASE3_COMPLETE.md`
- **Example**: `examples/orchestrator_example.py`

## Architecture Components

1. **StateBackend** - Key-value storage for caching
2. **AdRequest/AdResponse** - Universal request/response types
3. **ChainResolver** - VAST wrapper chain resolution
4. **VastProtocolHandler** - VAST protocol implementation
5. **Orchestrator** - High-level ad serving API

## Next Steps

The Phase 3 implementation provides the foundation for:
- Adding OpenRTB protocol handler
- Adding DAAST/audio VAST support
- Implementing additional state backends
- Advanced caching strategies
- Metrics and monitoring
