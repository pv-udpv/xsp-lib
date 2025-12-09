"""Basic HTTP upstream example."""

import asyncio

from xsp.core.base import BaseUpstream
from xsp.transports.http import HttpTransport


async def main():
    """Demonstrate basic HTTP upstream usage."""
    # Create HTTP upstream
    transport = HttpTransport()
    upstream = BaseUpstream(
        transport=transport,
        decoder=lambda b: b.decode("utf-8"),
        endpoint="https://httpbin.org/get",
    )

    # Fetch data
    print("Fetching data from httpbin.org...")
    result = await upstream.fetch(params={"key": "value"})
    print(f"Response:\n{result[:200]}...")

    # Cleanup
    await upstream.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
