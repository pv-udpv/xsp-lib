"""Example: Using the protocol-agnostic orchestrator with VAST."""

import asyncio

from xsp.orchestrator import AdRequest, Orchestrator
from xsp.protocols.vast import VastProtocolHandler, VastUpstream
from xsp.transports.memory import MemoryTransport


async def main() -> None:
    """Demonstrate orchestrator with VAST protocol."""
    # Sample VAST 4.2 XML response
    sample_vast = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="ad-123">
        <InLine>
            <AdSystem>ExampleAdSystem</AdSystem>
            <AdTitle>Example Video Ad</AdTitle>
            <Impression><![CDATA[https://track.example.com/impression]]></Impression>
            <Creatives>
                <Creative>
                    <Linear>
                        <Duration>00:00:30</Duration>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       bitrate="2000" width="1920" height="1080">
                                <![CDATA[https://cdn.example.com/ad.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""

    # Create VAST upstream with memory transport (for demo)
    transport = MemoryTransport(sample_vast.encode("utf-8"))
    vast_upstream = VastUpstream(
        transport=transport,
        endpoint="memory://vast",
    )

    # Create VAST protocol handler
    vast_handler = VastProtocolHandler(upstream=vast_upstream)

    # Create orchestrator with VAST handler
    orchestrator = Orchestrator(
        protocol_handler=vast_handler,
        enable_caching=True,  # Enable caching
        cache_ttl=3600,  # Cache for 1 hour
    )

    # Create protocol-agnostic ad request
    request = AdRequest(
        slot_id="pre-roll",
        user_id="user123",
        device_type="mobile",
        playhead_position=0.0,
    )

    print("=" * 60)
    print("Protocol-Agnostic Orchestrator Example")
    print("=" * 60)
    print()

    # Fetch ad
    print("Fetching ad...")
    response = await orchestrator.fetch_ad(request)

    print(f"Success: {response['success']}")
    print(f"Slot ID: {response['slot_id']}")

    if response["success"]:
        print(f"Ad ID: {response['ad_id']}")
        print(f"Creative Type: {response['creative_type']}")

        if "extensions" in response:
            print("\nVAST-specific extensions:")
            extensions = response["extensions"]
            if isinstance(extensions, dict):
                if "vast_xml" in extensions:
                    xml_preview = str(extensions["vast_xml"])[:100]
                    print(f"  VAST XML (first 100 chars): {xml_preview}...")
                if "params" in extensions:
                    print(f"  Parameters: {extensions['params']}")

        # Track impression event
        print("\nTracking impression event...")
        await orchestrator.track_event("impression", response)
        print("Impression tracked!")
    else:
        print(f"Error: {response.get('error', 'Unknown error')}")

    # Clean up
    await vast_upstream.close()

    print()
    print("=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
