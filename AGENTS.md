# Custom GitHub Copilot Agents

This repository uses custom GitHub Copilot agents to streamline development, testing, and documentation workflows. These agents are specialized AI assistants configured for specific tasks in the xsp-lib project.

## Available Agents

### 🎯 @orchestrator
**Role**: Planning and task coordination  
**File**: `.github/agents/orchestrator.md`

The orchestrator agent is your primary point of contact for complex tasks. It analyzes requirements, creates detailed execution plans, and delegates work to specialized agents.

**Use when:**
- Starting a new feature or protocol implementation
- Planning complex refactoring
- Coordinating multi-phase work (code + tests + docs)
- Need help breaking down large tasks

**Example:**
```
@orchestrator Please implement OpenRTB 2.6 protocol support with full tests and documentation
```

### 💻 @developer
**Role**: Code implementation  
**File**: `.github/agents/developer.md`

Expert Python developer specializing in AdTech protocols, async programming, and type-safe implementations. Writes production-ready code following project standards.

**Use when:**
- Implementing new protocols (VAST, OpenRTB, etc.)
- Writing core abstractions and utilities
- Fixing bugs in existing code
- Refactoring code structure
- Adding type hints and ensuring mypy compliance

**Example:**
```
@developer Implement VAST wrapper resolution with max depth tracking per VAST 4.2 spec
```

### 🧪 @tester
**Role**: Testing and quality assurance  
**File**: `.github/agents/tester.md`

Expert test engineer who writes comprehensive pytest tests, including async test patterns, fixtures, and protocol validation against IAB standards.

**Use when:**
- Writing unit tests for new code
- Creating integration tests
- Developing test fixtures
- Improving test coverage
- Testing edge cases and error handling
- Validating IAB specification compliance

**Example:**
```
@tester Create comprehensive tests for VAST macro substitution including all standard macros
```

### 📝 @doc-writer
**Role**: Documentation specialist  
**File**: `.github/agents/doc-writer.md`

Expert technical writer who creates clear API documentation, tutorials, and protocol guides with IAB specification references.

**Use when:**
- Documenting new APIs or protocols
- Writing tutorials and quickstart guides
- Creating usage examples
- Updating README
- Writing migration guides
- Documenting architecture

**Example:**
```
@doc-writer Create getting started guide for VAST protocol with complete examples
```

## How to Use Agents

### In GitHub Copilot Chat

Use the `@` syntax to invoke specific agents:

```
@orchestrator I need to implement OpenRTB 2.6 support
```

### Agent Workflow

For comprehensive features, follow this workflow:

1. **Planning Phase**: Start with @orchestrator
   ```
   @orchestrator Plan implementation of OpenRTB 2.6 protocol
   ```

2. **Development Phase**: @orchestrator delegates to @developer
   ```
   @developer implements core protocol code
   ```

3. **Testing Phase**: @orchestrator delegates to @tester
   ```
   @tester creates comprehensive test suite
   ```

4. **Documentation Phase**: @orchestrator delegates to @doc-writer
   ```
   @doc-writer documents the new protocol
   ```

5. **Integration**: @orchestrator validates completion

### Direct Agent Usage

You can also invoke agents directly for focused tasks:

```bash
# For a quick bug fix
@developer Fix the VAST wrapper resolution timeout issue

# For adding tests
@tester Add edge case tests for OpenRTB bid validation

# For documentation updates
@doc-writer Update README with new installation instructions
```

## Agent Capabilities

### Tools and Permissions

Each agent has access to specific tools:

| Agent | Tools |
|-------|-------|
| @orchestrator | All tools (*) |
| @developer | bash, edit, create, view, gh-advisory-database |
| @tester | bash, edit, create, view |
| @doc-writer | edit, create, view |

### Expertise Areas

| Agent | Primary Expertise |
|-------|------------------|
| @orchestrator | Task planning, delegation, coordination |
| @developer | Python async, type safety, AdTech protocols, IAB specs |
| @tester | pytest, async testing, coverage, protocol validation |
| @doc-writer | API docs, tutorials, markdown, code examples |

## Project-Specific Context

All agents understand xsp-lib project specifics:

### Technology Stack
- Python 3.11+ with strict typing
- Async/await patterns (asyncio)
- Protocol-based abstractions (typing.Protocol)
- pytest with pytest-asyncio for testing
- mypy --strict for type checking
- ruff and black for code style

### AdTech Protocols
- VAST 3.0-4.2 (video ad serving)
- OpenRTB 2.6, 3.0 (real-time bidding)
- DAAST (deprecated - use VAST 4.1+ with adType="audio")
- IAB Tech Lab specifications

### Project Structure
```
xsp-lib/
├── src/xsp/
│   ├── core/          # Base abstractions
│   ├── protocols/     # VAST, OpenRTB, etc.
│   ├── transports/    # HTTP, file, memory
│   ├── middleware/    # Retry, circuit breaker
│   └── utils/         # Utilities
├── tests/
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── fixtures/      # Test data
└── docs/
    ├── protocols/     # Protocol documentation
    └── guides/        # How-to guides
```

## Best Practices

### When to Use Which Agent

**Simple tasks** (use specific agent directly):
- Bug fix → @developer
- Add test → @tester
- Update docs → @doc-writer

**Complex tasks** (start with @orchestrator):
- New protocol implementation
- Major refactoring
- Multi-component features
- Cross-cutting changes

### Tips for Effective Agent Use

1. **Be specific**: Provide clear requirements and context
   ```
   ❌ @developer Fix VAST
   ✅ @developer Fix VAST wrapper resolution timeout when max depth is reached
   ```

2. **Include references**: Mention issue numbers and specs
   ```
   ✅ @developer Implement OpenRTB 2.6 per issue #3 following IAB spec section 3.2
   ```

3. **Specify constraints**: Mention any limitations
   ```
   ✅ @tester Add tests but don't modify existing passing tests
   ```

4. **Request explanations**: Ask agents to explain their approach
   ```
   ✅ @orchestrator Plan OpenRTB implementation and explain the approach
   ```

## Agent Limitations

### What Agents Cannot Do

- Merge pull requests
- Modify GitHub issues or PR descriptions
- Access private external resources
- Execute arbitrary shell commands without approval
- Bypass security policies

### When to Not Use Agents

- Simple text edits (do manually)
- Reviewing human judgment calls
- Making architectural decisions (get human input)
- Emergency hotfixes (review carefully)

## Feedback and Improvements

Agents are configured in `.github/agents/*.md` files. To improve agent behavior:

1. Review agent configuration files
2. Submit PR with improvements
3. Test with realistic scenarios
4. Document changes in this file

## Examples

### Example 1: Implementing New Protocol

```
User: @orchestrator I need to implement VAST 4.2 protocol support

@orchestrator creates plan:
- Phase 1: @developer implements VAST types and upstream
- Phase 2: @tester creates test suite with IAB examples
- Phase 3: @doc-writer documents VAST implementation
- Phase 4: Integration validation

User approves plan, agents execute sequentially
```

### Example 2: Bug Fix

```
User: @developer Fix wrapper resolution timeout in VastUpstream

@developer:
- Analyzes code in src/xsp/protocols/vast/upstream.py
- Identifies timeout issue
- Implements fix with proper error handling
- Adds type safety checks
- References VAST 4.2 spec in comments
```

### Example 3: Adding Tests

```
User: @tester Add tests for VAST macro substitution

@tester:
- Creates test_vast_macros.py
- Implements parametrized tests for all standard macros
- Uses IAB specification examples
- Adds edge case tests
- Ensures >85% coverage
```

### Example 4: Documentation

```
User: @doc-writer Create quickstart guide for VAST

@doc-writer:
- Creates docs/guides/getting-started-vast.md
- Includes installation instructions
- Adds step-by-step tutorial
- Provides complete code examples
- References IAB VAST specification
- Updates main docs index
```

## Troubleshooting

### Agent Not Responding

1. Check agent name is correct (@orchestrator, @developer, @tester, @doc-writer)
2. Ensure you're using GitHub Copilot Chat
3. Verify agents are in `.github/agents/` directory
4. Check agent file has proper YAML frontmatter

### Agent Gives Unexpected Results

1. Provide more specific instructions
2. Include relevant context and file paths
3. Reference issue numbers and specifications
4. Try breaking down the request into smaller tasks

### Agent Conflicts with Project Standards

1. Review agent configuration in `.github/agents/`
2. Update agent instructions to match current standards
3. Submit PR with improvements
4. Document the change in agent file

## Related Documentation

- [GitHub Copilot Custom Agents Documentation](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/create-custom-agents)
- [xsp-lib Repository Instructions](.github/copilot-instructions.md)
- [xsp-lib Architecture](docs/architecture.md)

## Version History

- v1.0 (2025-12): Initial agent configuration with orchestrator, developer, tester, and doc-writer
