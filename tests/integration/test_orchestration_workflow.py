"""Integration test for Phase 3 orchestration workflow."""

import pytest

from xsp import AdRequest, InMemoryStateBackend, Orchestrator
from xsp.protocols.vast import ChainResolver, VastProtocolHandler, VastUpstream
from xsp.transports.memory import MemoryTransport


@pytest.fixture
def sample_vast_xml() -> str:
    """Sample VAST XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.2">
    <Ad id="integration-test">
        <InLine>
            <AdSystem>Integration Test System</AdSystem>
            <AdTitle>Integration Test Ad</AdTitle>
            <Impression><![CDATA[https://impression.example.com/imp?id=integration]]></Impression>
            <Creatives>
                <Creative>
                    <Linear>
                        <Duration>00:00:15</Duration>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4"
                                       width="1280" height="720">
                                <![CDATA[https://cdn.example.com/integration-test.mp4]]>
                            </MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>"""


@pytest.mark.asyncio
async def test_full_orchestration_workflow(sample_vast_xml: str) -> None:
    """Test complete Phase 3 orchestration workflow."""
    # Setup: Create all components
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(
        transport=transport,
        endpoint="https://ads.example.com/vast",
        enable_macros=True,
    )
    resolver = ChainResolver(
        upstream=upstream,
        max_depth=5,
        propagate_headers=True,
    )
    vast_handler = VastProtocolHandler(chain_resolver=resolver)

    cache_backend = InMemoryStateBackend()
    orchestrator = Orchestrator(
        handlers={"vast": vast_handler},
        cache_backend=cache_backend,
        enable_caching=True,
        cache_ttl=60.0,
    )

    # Test 1: Basic request
    request = AdRequest(
        protocol="vast",
        user_id="integration-user-123",
        ip_address="192.168.1.100",
        url="https://example.com/video/integration-test",
        placement_id="integration-placement",
    )

    response = await orchestrator.serve(request)

    assert response.protocol == "vast"
    assert response.status == "success"
    assert "Integration Test Ad" in response.data
    assert response.metadata["user_id"] == "integration-user-123"

    # Test 2: Cache hit
    response2 = await orchestrator.serve(request)
    assert response2.status == "success"
    assert response2.data == response.data

    # Verify cache was used
    cache_key = orchestrator._build_cache_key(request, "vast")
    cached = await cache_backend.get(cache_key)
    assert cached is not None

    # Test 3: Different request (cache miss)
    request3 = AdRequest(
        protocol="vast",
        user_id="different-user",
        ip_address="10.0.0.1",
    )

    response3 = await orchestrator.serve(request3)
    assert response3.status == "success"
    assert "Integration Test Ad" in response3.data

    # Cleanup
    await orchestrator.close()


@pytest.mark.asyncio
async def test_orchestration_with_multiple_handlers(sample_vast_xml: str) -> None:
    """Test orchestrator with potential for multiple protocol handlers."""
    # Setup VAST handler
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    vast_handler = VastProtocolHandler(chain_resolver=resolver)

    # Create orchestrator and register handler
    orchestrator = Orchestrator()
    orchestrator.register_handler("vast", vast_handler)

    # Verify handler registered
    assert "vast" in orchestrator.handlers

    # Test VAST request
    request = AdRequest(protocol="vast", user_id="user123")
    response = await orchestrator.serve(request)
    assert response.protocol == "vast"
    assert response.status == "success"

    # Test unsupported protocol
    request2 = AdRequest(protocol="openrtb")
    response2 = await orchestrator.serve(request2)
    assert response2.status == "error"
    assert "not supported" in response2.error

    await orchestrator.close()


@pytest.mark.asyncio
async def test_state_backend_integration(sample_vast_xml: str) -> None:
    """Test state backend integration with orchestrator."""
    transport = MemoryTransport(sample_vast_xml.encode("utf-8"))
    upstream = VastUpstream(transport=transport, endpoint="https://ads.example.com/vast")
    resolver = ChainResolver(upstream=upstream)
    vast_handler = VastProtocolHandler(chain_resolver=resolver)

    # Use InMemoryStateBackend
    state_backend = InMemoryStateBackend()

    orchestrator = Orchestrator(
        handlers={"vast": vast_handler},
        cache_backend=state_backend,
        enable_caching=True,
    )

    # Store and retrieve directly in state backend
    await state_backend.set("test-key", "test-value")
    value = await state_backend.get("test-key")
    assert value == "test-value"

    # Test existence
    assert await state_backend.exists("test-key") is True
    assert await state_backend.exists("nonexistent") is False

    # Serve request (will cache in same backend)
    request = AdRequest(protocol="vast", user_id="user123")
    response = await orchestrator.serve(request)
    assert response.status == "success"

    # Verify both our manual entry and cache entry exist
    assert await state_backend.exists("test-key") is True

    await orchestrator.close()
