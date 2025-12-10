"""Example demonstrating the Orchestrator for protocol-agnostic ad serving."""

import asyncio

from xsp import AdRequest, InMemoryStateBackend, Orchestrator
from xsp.protocols.vast import ChainResolver, VastProtocolHandler, VastUpstream
from xsp.transports.memory import MemoryTransport


async def main() -> None:
    """Demonstrate orchestrator with VAST protocol handler."""
    # Sample VAST XML response
    vast_xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="12345">
        <InLine>
            <AdSystem>Example Ad Server</AdSystem>
            <AdTitle>Sample Video Ad</AdTitle>
            <Impression><![CDATA[https://impression.example.com/imp?id=123]]></Impression>
            <Creatives>
                <Creative>
                    <Linear>
                        <Duration>00:00:30</Duration>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1920" height="1080" bitrate="2500">
                                <![CDATA[https://cdn.example.com/video.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                        <VideoClicks>
                            <ClickThrough><![CDATA[https://example.com/click]]></ClickThrough>
                        </VideoClicks>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""

    # Setup VAST handler
    print("Setting up VAST protocol handler...")
    transport = MemoryTransport(vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream, max_depth=5)
    vast_handler = VastProtocolHandler(chain_resolver=resolver)

    # Setup orchestrator with caching
    print("Creating orchestrator with caching enabled...")
    cache_backend = InMemoryStateBackend()
    orchestrator = Orchestrator(
        handlers={"vast": vast_handler},
        cache_backend=cache_backend,
        enable_caching=True,
        cache_ttl=300.0,  # 5 minutes
    )

    # Example 1: Basic VAST request
    print("\n=== Example 1: Basic VAST Request ===")
    request = AdRequest(
        protocol="vast",
        user_id="user123",
        ip_address="192.168.1.1",
        url="https://example.com/video/page",
        placement_id="homepage-banner",
    )

    response = await orchestrator.serve(request)
    print(f"Protocol: {response.protocol}")
    print(f"Status: {response.status}")
    print(f"Data length: {len(response.data)} bytes")
    print(f"Contains VAST: {'<VAST' in response.data}")
    print(f"User ID from metadata: {response.metadata.get('user_id')}")

    # Example 2: Request with auto-detection (no protocol specified)
    print("\n=== Example 2: Auto-detect Protocol ===")
    request = AdRequest(
        user_id="user456",
        ip_address="10.0.0.1",
    )

    response = await orchestrator.serve(request)
    print(f"Auto-detected protocol: {response.protocol}")
    print(f"Status: {response.status}")

    # Example 3: Cached request
    print("\n=== Example 3: Cached Request ===")
    request = AdRequest(
        protocol="vast",
        user_id="user123",
        ip_address="192.168.1.1",
        url="https://example.com/video/page",
        placement_id="homepage-banner",
    )

    # First request (already served above, should hit cache)
    response = await orchestrator.serve(request)
    print(f"Response from cache: {response.status}")
    print(f"Same data: {len(response.data)} bytes")

    # Example 4: Additional parameters
    print("\n=== Example 4: Additional Parameters ===")
    request = AdRequest(
        protocol="vast",
        user_id="user789",
        params={
            "format": "video",
            "duration": "30",
            "min_bitrate": "1000",
        },
    )

    response = await orchestrator.serve(request)
    print(f"Status: {response.status}")
    print(f"Parameters passed: {response.metadata.get('params')}")

    # Example 5: Unsupported protocol
    print("\n=== Example 5: Unsupported Protocol ===")
    request = AdRequest(protocol="openrtb")

    response = await orchestrator.serve(request)
    print(f"Status: {response.status}")
    print(f"Error: {response.error}")
    print(f"Supported protocols: {response.metadata.get('supported_protocols')}")

    # Cleanup
    print("\n=== Cleanup ===")
    await orchestrator.close()
    print("Resources released")


if __name__ == "__main__":
    asyncio.run(main())
