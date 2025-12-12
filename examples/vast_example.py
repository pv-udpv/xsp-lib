"""VAST protocol example."""

import asyncio

from xsp.protocols.vast import VastUpstream, VastVersion
from xsp.transports.memory import MemoryTransport


async def main() -> None:
    """Demonstrate VAST upstream usage."""
    # Sample VAST XML
    sample_vast = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="12345">
        <InLine>
            <AdSystem>TestSystem</AdSystem>
            <AdTitle>Sample VAST Advertisement</AdTitle>
            <Impression><![CDATA[https://impression.example.com/imp?id=123]]></Impression>
            <Creatives>
                <Creative>
                    <Linear>
                        <Duration>00:00:30</Duration>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1920" height="1080">
                                <![CDATA[https://cdn.example.com/sample_video.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""

    # Create VAST upstream with memory transport
    transport = MemoryTransport(sample_vast.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="memory://vast",
        version=VastVersion.V4_2,
        enable_macros=True,
        validate_xml=True,
    )

    # Request VAST XML
    print("Requesting VAST XML...")
    vast_xml = await upstream.request()
    print(f"VAST XML ({len(vast_xml)} bytes):\n{vast_xml[:200]}...\n")

    # Create a session
    session = upstream.create_session(vast_xml)
    print(f"Created VAST session: {session['session_id']}")

    # Cleanup
    await upstream.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
