# MCP Quick Reference Guide

Quick reference for using Model Context Protocol (MCP) with GitHub Copilot in xsp-lib.

## Quick Start

### Prerequisites
```bash
# Check Node.js (required for MCP)
node --version  # Should be v16+

# Verify MCP config
python -m json.tool < .github/copilot/mcp.json
```

### Using MCP-Enhanced Agents

```bash
# Protocol implementation with spec access
@developer Implement VAST wrapper resolution per VAST 4.2 section 2.4.3.4

# Test generation with validation
@tester Create OpenRTB bid validation tests per OpenRTB 2.6

# Documentation with references
@doc-writer Document VastUpstream with spec references

# Planning with context
@orchestrator Plan frequency capping implementation
```

## Available MCP Servers

| Server | Capabilities | Use For |
|--------|-------------|---------|
| **filesystem** | Read/write files, search code | Code navigation, understanding structure |
| **github** | Issues, PRs, discussions | Task context, related work |
| **python** | Run code, tests, type checking | Validation, testing, analysis |
| **web** | Fetch IAB specs | Protocol specifications, standards |
| **memory** | Store/retrieve context | Session continuity |
| **rope-refactor** | Rename, extract, inline, organize imports | Safe code refactoring |

## Agent MCP Access

| Agent | MCP Servers | Enhanced For |
|-------|-------------|-------------|
| `@developer` | filesystem, github, python, web, rope-refactor | Spec-compliant implementation, refactoring |
| `@tester` | filesystem, python | Protocol validation tests |
| `@doc-writer` | filesystem, web | Accurate documentation |
| `@orchestrator` | filesystem, github, memory | Coordinated planning |

## Common Patterns

### Pattern 1: Spec-Driven Implementation
```bash
@developer Implement [feature] per [protocol] [version] section [X.Y.Z]
```
**MCP Flow**: Web → Fetch spec → Filesystem → Read code → Implement

### Pattern 2: Protocol-Validated Tests
```bash
@tester Create tests for [feature] covering [requirements] per [spec]
```
**MCP Flow**: Web → Fetch spec → Filesystem → Read code → Generate tests → Python → Run tests

### Pattern 3: Accurate Documentation
```bash
@doc-writer Document [component] with spec references and examples
```
**MCP Flow**: Filesystem → Read code → Web → Fetch specs → Create docs

### Pattern 4: Context-Aware Planning
```bash
@orchestrator Plan [feature] implementation
```
**MCP Flow**: GitHub → Check issues → Filesystem → Analyze code → Memory → Store plan

## Specification Access

MCP enables direct access to:
- **VAST**: https://iabtechlab.com/standards/vast/
- **OpenRTB**: https://github.com/InteractiveAdvertisingBureau/openrtb
- **Python Docs**: https://docs.python.org/

## Command Cheat Sheet

### Protocol Implementation
```bash
# VAST feature
@developer Implement VAST [feature] per VAST 4.2 §[section]

# OpenRTB feature
@developer Implement OpenRTB [feature] per OpenRTB 2.6 §[section]
```

### Testing
```bash
# Unit tests
@tester Create unit tests for [component] with [coverage]% coverage

# Integration tests
@tester Create integration tests for [feature] workflow

# Protocol validation
@tester Add validation tests per [spec] section [X.Y.Z]
```

### Documentation
```bash
# API docs
@doc-writer Document [class/function] with examples

# Guide
@doc-writer Create guide for [feature] with spec references

# README update
@doc-writer Update README with [section] information
```

### Refactoring
```bash
# Safe rename
@developer Rename [old_name] to [new_name] across the codebase

# Extract method
@developer Extract [code_block_description] into a separate method

# Organize imports
@developer Organize and optimize imports in [module]

# Extract variable
@developer Extract [expression] into a well-named variable
```

### Planning
```bash
# Feature planning
@orchestrator Plan implementation of [feature]

# Status check
@orchestrator Review current phase status and next steps

# Multi-phase coordination
@orchestrator Coordinate [feature] implementation across code/tests/docs
```

## Troubleshooting

### Issue: MCP not working
```bash
# Check prerequisites
node --version
npx -y @modelcontextprotocol/server-filesystem --help

# Validate config
python -m json.tool < .github/copilot/mcp.json
```

### Issue: Cannot fetch specs
```bash
# Test connectivity
curl -I https://iabtechlab.com

# Check allowed domains
grep -A 5 allowedDomains .github/copilot/mcp.json
```

### Issue: Agent not using MCP
**Check:**
- Using GitHub Copilot Chat (not inline)
- Repository open in IDE
- Using `@agent` mention syntax
- MCP config file exists

## Best Practices

### ✅ DO
- Reference specific spec sections
- Mention issue numbers when relevant
- Use orchestrator for complex tasks
- Be specific about requirements
- Let MCP provide context automatically

### ❌ DON'T
- Make vague requests without context
- Skip spec references for protocol work
- Use inline completion for MCP features
- Assume agent knows recent changes

## Examples

### Example 1: Implement Protocol Feature
```bash
# Request
@developer Implement VAST extension support per VAST 4.2 section 2.4.5.1

# What happens
1. Fetches VAST 4.2 spec section 2.4.5.1
2. Reads existing VAST code structure
3. Implements extension parsing
4. Adds type hints
5. Validates with mypy
```

### Example 2: Generate Tests
```bash
# Request
@tester Create tests for VAST macro substitution covering all standard macros

# What happens
1. Fetches VAST macro specification
2. Reads macro substitution code
3. Generates parametrized tests
4. Includes edge cases
5. Runs tests to verify
```

### Example 3: Document Feature
```bash
# Request
@doc-writer Document VastUpstream configuration options

# What happens
1. Reads VastUpstream code
2. Fetches relevant VAST spec sections
3. Creates comprehensive docs
4. Adds code examples
5. Includes spec references
```

## Resource Links

- [Full MCP Guide](mcp-integration.md)
- [Detailed Examples](mcp-examples.md)
- [Custom Agents](../../AGENTS.md)
- [GitHub MCP Docs](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/extend-coding-agent-with-mcp)

---

**Version**: 1.0  
**Last Updated**: December 10, 2025  
**Quick Reference for**: xsp-lib developers using GitHub Copilot with MCP
