# Model Context Protocol (MCP) Integration

## Overview

The xsp-lib repository is enhanced with Model Context Protocol (MCP) integration, which extends GitHub Copilot's capabilities with specialized tools and context providers for AdTech protocol development.

## What is MCP?

Model Context Protocol (MCP) is an open standard that enables AI assistants like GitHub Copilot to securely connect to external data sources and tools. For xsp-lib, this means Copilot can:

- Access IAB AdTech specifications directly
- Navigate the repository more intelligently
- Run Python tests and analyze code
- Maintain context across development sessions
- Leverage domain-specific knowledge about VAST, OpenRTB, and other protocols

## Configuration

The MCP configuration is defined in `.github/copilot/mcp.json` and includes:

### MCP Servers

#### 1. Filesystem Server
- **Purpose**: Repository navigation and code access
- **Capabilities**: Read/write files, list directories, search code
- **Use cases**: 
  - Understanding project structure
  - Finding related code
  - Reading test fixtures

#### 2. GitHub Server
- **Purpose**: Access to GitHub API for issues, PRs, and discussions
- **Capabilities**: Read issues, pull requests, search code
- **Use cases**:
  - Understanding task context
  - Finding related issues
  - Checking PR history

#### 3. Python Server
- **Purpose**: Python development tools
- **Capabilities**: Run Python code, analyze code, execute tests
- **Use cases**:
  - Running pytest tests
  - Type checking with mypy
  - Code analysis

#### 4. Web Server
- **Purpose**: Access to external documentation
- **Capabilities**: Fetch URLs, search web (limited to allowed domains)
- **Allowed domains**:
  - `iabtechlab.com` - IAB specifications
  - `github.com` - Open source references
  - `docs.python.org` - Python documentation
  - `openrtb.github.io` - OpenRTB specs
- **Use cases**:
  - Fetching VAST/OpenRTB specifications
  - Checking IAB Tech Lab standards
  - Referencing protocol documentation

#### 5. Memory Server
- **Purpose**: Persistent context across sessions
- **Capabilities**: Store context, retrieve context, semantic search
- **Use cases**:
  - Remembering project conventions
  - Tracking implementation progress
  - Maintaining conversation context

## Context Providers

### Repository Context
Automatically provides context from:
- Source code (`src/xsp/**/*.py`)
- Tests (`tests/**/*.py`)
- Documentation (`docs/**/*.md`)
- Project configuration (`pyproject.toml`, `README.md`)

### Specifications Context
Direct access to IAB specifications:
- VAST (Video Ad Serving Template)
- OpenRTB (Open Real-Time Bidding)
- Related AdTech standards

### Development Context
GitHub project context:
- Open issues and their history
- Pull requests and reviews
- Project discussions

## Tool Enhancements

### Code Generation
Enhanced with preferences for:
- **Type hints**: Strict typing with mypy
- **Docstring style**: Google-style docstrings
- **Async patterns**: Modern async/await usage
- **Test framework**: pytest with fixtures

### Protocol Analysis
Specialized support for AdTech protocols:
- VAST 3.0, 4.0, 4.1, 4.2
- VPAID, VMAP
- OpenRTB 2.5, 2.6, 3.0
- DAAST, CATS, AdCOM

### Test Generation
Intelligent test creation with:
- Coverage target: 85%+
- Async test patterns
- Pytest fixtures
- Parametrized tests

## Agent-Specific Enhancements

### @developer Agent
**MCP Servers**: filesystem, github, python, web
**Enhanced with**:
- IAB specification compliance checking
- Python async/await best practices
- Type safety validation

### @tester Agent
**MCP Servers**: filesystem, python
**Enhanced with**:
- pytest fixtures and parametrization patterns
- Async test patterns for protocol testing
- Protocol validation test cases

### @doc-writer Agent
**MCP Servers**: filesystem, web
**Enhanced with**:
- Technical writing best practices
- API documentation standards
- IAB specification references

### @orchestrator Agent
**MCP Servers**: filesystem, github, memory
**Enhanced with**:
- Project architecture understanding
- Task dependency analysis
- Team coordination patterns

## Usage Examples

### Example 1: Protocol Implementation with Specification Access

```bash
# Copilot can now fetch VAST 4.2 spec while implementing
@developer Implement VAST wrapper resolution per VAST 4.2 section 2.4.3.4
```

The developer agent will:
1. Use the **web server** to fetch VAST 4.2 specification
2. Use the **filesystem server** to read existing code
3. Use the **github server** to check related issues
4. Implement code following the specification
5. Use the **python server** to validate the implementation

### Example 2: Test Generation with Context

```bash
@tester Create tests for OpenRTB bid validation covering all required fields per OpenRTB 2.6
```

The tester agent will:
1. Use the **web server** to fetch OpenRTB 2.6 specification
2. Use the **filesystem server** to read existing tests
3. Generate comprehensive tests with proper fixtures
4. Use the **python server** to run the tests

### Example 3: Documentation with Specification References

```bash
@doc-writer Document VAST upstream configuration with examples and spec references
```

The doc-writer agent will:
1. Use the **web server** to fetch relevant specification sections
2. Use the **filesystem server** to read the implementation
3. Create documentation with accurate spec references
4. Include working code examples

### Example 4: Planning with Memory

```bash
@orchestrator Review the current Phase 1 status and plan next steps
```

The orchestrator agent will:
1. Use the **github server** to read project issues and PRs
2. Use the **memory server** to recall previous planning decisions
3. Use the **filesystem server** to check current implementation status
4. Create a comprehensive plan with context

## Security Policies

### Allowed Operations
- ✅ Read repository files
- ✅ Write repository files (in working directory)
- ✅ Read GitHub issues and PRs
- ✅ Fetch IAB specifications
- ✅ Run tests locally
- ✅ Analyze code

### Restricted Operations
- ❌ Modify GitHub issues directly
- ❌ Create pull requests via API
- ❌ Publish packages
- ❌ Modify secrets or credentials

### Data Retention
- **Memory**: Session-based (cleared after session)
- **Logs**: 24 hours maximum retention

## Setup and Configuration

### Prerequisites

1. **Node.js**: Required for MCP server runners (npx)
2. **GitHub Token**: Set `GITHUB_TOKEN` environment variable for GitHub server
3. **Internet Access**: Required for web server to fetch specifications

### Enabling MCP

MCP is automatically enabled when using GitHub Copilot with this repository. No manual setup required beyond ensuring prerequisites are met.

### GitHub Copilot Agent Environment Setup

The repository includes a dedicated workflow (`.github/workflows/copilot-setup-steps.yml`) that GitHub Copilot coding agent uses to prepare the development environment. This workflow:

- Installs Python 3.12 with Poetry
- Installs all project dependencies
- Sets up Node.js for MCP servers
- Verifies CLI tools (pytest, mypy, ruff)
- Validates MCP configuration

This ensures the agent has a fully configured environment before executing tasks.

### Verifying MCP Configuration

To verify MCP is working:

```bash
# Check if MCP configuration is valid
python -m json.tool < .github/copilot/mcp.json

# Verify MCP servers are accessible
npx -y @modelcontextprotocol/server-filesystem --help
```

## Troubleshooting

### Issue: MCP Servers Not Found

**Symptom**: Copilot cannot access MCP capabilities
**Solution**: Ensure Node.js and npx are installed:
```bash
node --version
npx --version
```

### Issue: GitHub Server Authentication

**Symptom**: Cannot access GitHub context
**Solution**: Set GITHUB_TOKEN environment variable:
```bash
export GITHUB_TOKEN=your_token_here
```

### Issue: Web Server Cannot Fetch Specifications

**Symptom**: Cannot access IAB specifications
**Solution**: 
1. Check internet connectivity
2. Verify allowed domains in mcp.json
3. Ensure no firewall blocks

### Issue: Memory Not Persisting

**Symptom**: Context lost between sessions
**Solution**: Memory is session-based by design for security. Use explicit documentation for persistent information.

## Best Practices

### 1. Leverage Specification Access

Instead of asking Copilot to "guess" protocol behavior, reference specs directly:

```bash
# ✅ Good: Specific with spec reference
@developer Implement VAST inline elements per VAST 4.2 section 2.4.2.2

# ❌ Less effective: Vague request
@developer Add VAST inline support
```

### 2. Use Context Providers

Let MCP provide context automatically:

```bash
# Copilot will automatically check related issues and code
@orchestrator Plan implementation for frequency capping feature
```

### 3. Combine Multiple Servers

Complex tasks benefit from multiple MCP servers:

```bash
# Uses filesystem + web + python servers
@developer Implement and test VPAID validation per VPAID 2.0 spec
```

### 4. Trust Memory for Session Context

The memory server maintains context within a session:

```bash
# First interaction
@orchestrator I'm working on Phase 1: SessionContext implementation

# Later in same session - orchestrator remembers
@orchestrator What's the next step?
```

## Future Enhancements

Potential future MCP integrations:

1. **Custom xsp-lib MCP Server**
   - Protocol-specific validation
   - Custom test fixture generation
   - AdTech terminology reference

2. **Redis MCP Server**
   - State backend testing
   - Cache simulation

3. **IAB Spec Validator Server**
   - Real-time specification compliance checking
   - Version-specific validation

4. **Performance Profiling Server**
   - Async performance analysis
   - Memory usage tracking

## Related Documentation

- [GitHub Copilot MCP Documentation](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/extend-coding-agent-with-mcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [xsp-lib Custom Agents](../../AGENTS.md)
- [Contributing Guidelines](../../CONTRIBUTING.md)

## Feedback and Contributions

If you have suggestions for improving MCP integration:

1. Open an issue with label `mcp-enhancement`
2. Describe the proposed enhancement
3. Explain the use case and benefits
4. Submit a PR with changes to `.github/copilot/mcp.json`

---

**Last Updated**: December 10, 2025
**Version**: 1.0
**Status**: Active
