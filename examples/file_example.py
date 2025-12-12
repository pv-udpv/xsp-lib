"""Example using file transport for testing."""

import asyncio
import json
from pathlib import Path

from xsp.core.base import BaseUpstream
from xsp.transports.file import FileTransport


async def main():
    """Demonstrate file transport usage."""
    # Create file transport
    transport = FileTransport()

    # Get the test fixtures path
    fixtures_path = Path(__file__).parent.parent / "tests" / "fixtures" / "samples" / "sample.json"

    # Create upstream with JSON decoder
    upstream = BaseUpstream(
        transport=transport,
        decoder=json.loads,
        endpoint=str(fixtures_path),
    )

    # Request data
    print(f"Requesting data from: {fixtures_path}")
    result = await upstream.request()
    print(f"Response: {result}")
    print(f"Service: {result['service']}")
    print(f"Protocols: {', '.join(result['protocols'])}")

    # Cleanup
    await upstream.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
