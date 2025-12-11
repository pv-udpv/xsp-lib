"""Example using memory transport for testing."""

import asyncio

from xsp.core.base import BaseUpstream
from xsp.transports.memory import MemoryTransport


async def main():
    """Demonstrate memory transport usage."""
    # Create memory transport with sample data
    transport = MemoryTransport(b'{"message": "Hello from xsp-lib!", "status": "ok"}')

    # Create upstream with JSON decoder
    import json

    upstream = BaseUpstream(
        transport=transport,
        decoder=json.loads,
        endpoint="memory://test",
    )

    # Request data
    print("Requesting data from memory transport...")
    result = await upstream.request()
    print(f"Response: {result}")
    print(f"Message: {result['message']}")

    # Cleanup
    await upstream.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
