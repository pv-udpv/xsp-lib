# Quick Start Guide

This guide will help you get started with **xsp-lib** in minutes.

## Installation

Install xsp-lib with the HTTP transport:

```bash
pip install xsp-lib[http]
```

## Your First Upstream

Create a simple HTTP upstream to fetch data:

```python
import asyncio
from xsp.core.base import BaseUpstream
from xsp.transports.http import HttpTransport

async def main():
    # Create HTTP transport
    transport = HttpTransport()
    
    # Create upstream
    upstream = BaseUpstream(
        transport=transport,
        decoder=lambda b: b.decode('utf-8'),
        endpoint="https://httpbin.org/get"
    )
    
    # Fetch data
    result = await upstream.fetch(params={"key": "value"})
    print(result)
    
    # Cleanup
    await upstream.close()

asyncio.run(main())
```

## Using Middleware

Add retry logic with middleware:

```python
from xsp.middleware.retry import RetryMiddleware
from xsp.middleware.base import MiddlewareStack

# Create middleware stack
middleware = MiddlewareStack(
    RetryMiddleware(max_attempts=3, backoff_base=2.0)
)

# Wrap upstream
upstream = middleware.wrap(base_upstream)
result = await upstream.fetch()
```

## Testing with File Transport

Use file-based transport for testing:

```python
from xsp.transports.file import FileTransport

transport = FileTransport()
upstream = BaseUpstream(
    transport=transport,
    decoder=lambda b: b.decode('utf-8'),
    endpoint="/path/to/test/data.xml"
)
```

## Next Steps

- Learn about the [Architecture](architecture.md)
- Explore [Protocol Implementations](protocols/)
- Read the [API Reference](api/)
