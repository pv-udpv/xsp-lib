# xsp-lib Documentation

Welcome to the **xsp-lib** documentation - the universal AdTech service protocol library.

## Overview

**xsp-lib** provides a comprehensive set of tools for working with AdTech protocols and standards:

- **Upstream Protocols**: VAST, OpenRTB, DAAST, CATS
- **Industry Standards**: OpenDirect, AdCOM, IAB specifications
- **Infrastructure**: Pluggable transports, middleware system, testing utilities

## Quick Links

- [Quick Start Guide](quickstart.md)
- [Architecture Overview](architecture.md)
- [API Reference](api/)
- [Protocol Documentation](protocols/)
- [Standards Documentation](standards/)

## Development Resources

- [MCP Integration Guide](development/mcp-integration.md) - Model Context Protocol for enhanced GitHub Copilot
- [MCP Examples](development/mcp-examples.md) - Practical examples using MCP with custom agents
- [MCP Quick Reference](development/mcp-quick-reference.md) - Quick command reference for MCP
- [Custom Agents](../AGENTS.md) - GitHub Copilot agent documentation

## Architecture Documentation

In-depth architecture documentation:

- [Final Architecture](architecture-final.md) - Complete system architecture with layers, components, and data flow
- [Session Management](architecture-session-management.md) - Stateful ad serving with frequency capping and budget tracking
- [Terminology Reference](architecture-terminology.md) - Precise terminology for each architectural layer
- [Protocol-Agnostic Design](architecture-protocol-agnostic-design.md) - Generic schemas and protocol handlers

## Installation

```bash
# Core library
pip install xsp-lib

# With HTTP transport
pip install xsp-lib[http]

# With specific protocols
pip install xsp-lib[vast,openrtb]

# Full installation
pip install xsp-lib[all]
```

## Basic Usage

```python
import asyncio
from xsp.core.base import BaseUpstream
from xsp.transports.http import HttpTransport

async def main():
    upstream = BaseUpstream(
        transport=HttpTransport(),
        decoder=lambda b: b.decode('utf-8'),
        endpoint="https://api.example.com/data"
    )
    
    result = await upstream.fetch()
    await upstream.close()

asyncio.run(main())
```

## Getting Help

- [GitHub Issues](https://github.com/pv-udpv/xsp-lib/issues)
- [Discussions](https://github.com/pv-udpv/xsp-lib/discussions)
