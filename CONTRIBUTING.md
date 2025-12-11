# Contributing to xsp-lib

Thank you for your interest in contributing to xsp-lib! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Issue Guidelines](#issue-guidelines)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Working with Copilot](#working-with-copilot)

## Code of Conduct

Be respectful, inclusive, and professional in all interactions. We're building tools for the AdTech community together.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- Familiarity with async Python programming
- Node.js (optional, for MCP integration with GitHub Copilot)

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/pv-udpv/xsp-lib.git
cd xsp-lib

# Install in development mode
pip install -e .[dev,http]

# ⚡ IMPORTANT: Install pre-commit hooks (auto-runs quality checks)
pre-commit install

# Verify installation
pytest --version
mypy --version
ruff --version
pre-commit --version

# Optional: Run all checks manually
pre-commit run --all-files
```

### ⚡ Pre-commit Hooks (Essential!)

**Pre-commit hooks automatically check and fix your code before each commit.**

After installation (`pre-commit install`), every `git commit` will:
- ✅ Auto-format code with `ruff format`
- ✅ Auto-fix lint issues with `ruff check --fix`
- ✅ Check types with `mypy --strict`
- ✅ Run unit tests with `pytest`
- ✅ Fix whitespace, YAML syntax, etc.

**This means you get instant feedback and auto-fixes WITHOUT waiting for CI!**

📖 **Detailed guide**: [.github/hooks/README.md](.github/hooks/README.md)

### GitHub Copilot with MCP (Optional)

This repository includes Model Context Protocol (MCP) integration for enhanced GitHub Copilot capabilities:

- **Automatic spec access**: Copilot can fetch IAB specifications during development
- **Smart context**: Enhanced understanding of repository structure and history
- **Better suggestions**: Protocol-aware code completion and generation

To enable MCP features:
1. Ensure Node.js is installed (v16+)
2. Use GitHub Copilot in your IDE
3. MCP will automatically activate when working in this repository

**For GitHub Copilot Coding Agent**: The repository includes `.github/workflows/copilot-setup-steps.yml` that automatically prepares the development environment with all dependencies, CLI tools, and MCP servers.

See [MCP Integration Guide](docs/development/mcp-integration.md) for details.

### Repository Structure

```
xsp-lib/
├── src/xsp/          # Source code
│   ├── core/         # Base abstractions
│   ├── protocols/    # VAST, OpenRTB, etc.
│   ├── transports/   # HTTP, file, memory
│   ├── middleware/   # Retry, circuit breaker
│   └── utils/        # Utilities
├── tests/            # Test suite
│   ├── unit/         # Unit tests
│   ├── integration/  # Integration tests
│   └── fixtures/     # Test data
├── docs/             # Documentation
└── examples/         # Example code
```

## Development Process

### 1. Find or Create an Issue

- Browse [existing issues](https://github.com/pv-udpv/xsp-lib/issues)
- Create a new issue using the appropriate template:
  - 🐛 Bug Report
  - ✨ Feature Request
  - 🔌 Protocol Implementation
  - 📝 Documentation
  - 🤖 Copilot Task

### 2. Fork and Branch

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/xsp-lib.git
cd xsp-lib

# Install pre-commit hooks (essential!)
pre-commit install

# Create a feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 3. Make Changes

- Write code following our [Coding Standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed
- Commit frequently with clear messages

**Pre-commit hooks will automatically check your code on each commit, auto-fixing formatting and lint issues where possible. Some checks (like type errors and test failures) will require manual fixes.**

### 4. Test Your Changes

**Pre-commit hooks automatically run all checks before each commit.**

No manual commands needed! Just `git commit` and hooks will:
1. Auto-format with ruff
2. Auto-fix lint issues
3. Check types with mypy
4. Run unit tests
5. Validate YAML/TOML

**Manual testing (optional):**
```bash
# Run all checks manually
pre-commit run --all-files

# Run specific checks
pytest
mypy src --strict
ruff check src tests
```

**Troubleshooting**: See [.github/hooks/README.md](.github/hooks/README.md)

### 5. Submit Pull Request

- Push your branch to your fork
- Create a Pull Request using the PR template
- Link to the related issue
- Respond to review feedback

## Issue Guidelines

### Bug Reports

Use the **🐛 Bug Report** template. Include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Minimal reproducible example
- Version information

### Feature Requests

Use the **✨ Feature Request** template. Include:
- Problem statement
- Proposed solution
- Example usage
- Specification references (if applicable)

### Protocol Implementation

Use the **🔌 Protocol Implementation** template for requesting new protocol support.

### Copilot Tasks

Use the **🤖 Copilot Task** template for well-defined tasks suitable for GitHub Copilot.

## Pull Request Process

### PR Requirements

1. **✅ Pre-commit installed**: Run `pre-commit install` (hooks auto-check everything!)
2. **Tests**: All new code must have tests
3. **Type Hints**: Use type hints everywhere (mypy --strict)
4. **Documentation**: Update docstrings and docs
5. **Quality**: Pass all checks (automated by pre-commit)

### PR Template

Use the Pull Request template. Fill out all relevant sections:
- Summary and related issue
- Type of change
- Testing performed
- Quality checks
- Documentation updates

### Review Process

1. Automated checks must pass (CI)
2. Code review by maintainer(s)
3. Address feedback via new commits
4. Maintainer merges when approved

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(vast): add wrapper resolution with max depth
fix(openrtb): correct bid validation logic
docs(api): update VastUpstream usage examples
test(vast): add macro substitution tests
refactor(core): simplify transport abstraction
chore(ci): update GitHub Actions workflow
```

## Coding Standards

### Python Style

- **Python Version**: 3.11+
- **Type Hints**: Required everywhere
- **Async/Await**: Use for all I/O operations
- **Line Length**: 100 characters
- **Formatter**: ruff format (auto-applied by pre-commit)
- **Linter**: ruff check (auto-fixed by pre-commit)

### Type Safety

```python
# ✅ GOOD: Strict typing
from typing import Protocol, TypeVar, Generic

T = TypeVar('T')

class Upstream(Protocol[T]):
    async def fetch(self, **params: Any) -> T: ...

# ❌ BAD: No types
def fetch(params):
    return do_something(params)
```

### Async Patterns

```python
# ✅ GOOD: Async context management
async def fetch_vast(url: str) -> VastResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return parse_vast(response.text)

# ❌ BAD: Blocking I/O
def fetch_vast(url: str) -> VastResponse:
    response = requests.get(url)  # Blocking!
    return parse_vast(response.text)
```

### Docstring Format

```python
async def fetch(
    self,
    params: dict[str, str] | None = None,
    timeout: float = 30.0
) -> VastResponse:
    """Fetch VAST ad from upstream service.
    
    Args:
        params: Query parameters for the request
        timeout: Request timeout in seconds
        
    Returns:
        Parsed VAST response object
        
    Raises:
        VastError: If VAST XML is invalid or malformed
        TimeoutError: If request exceeds timeout
        TransportError: If network request fails
        
    Example:
        >>> upstream = VastUpstream(...)
        >>> response = await upstream.fetch(params={"w": "640"})
    """
```

### IAB Specification References

When implementing protocols, reference specifications:

```python
async def resolve_wrapper(self, vast_url: str) -> VastInline:
    """Resolve VAST wrapper to inline ad.
    
    Per VAST 4.2 §2.4.3.4 - Wrapper elements must be
    resolved recursively up to maxwrapperdepth.
    
    References:
        - VAST 4.2: https://iabtechlab.com/standards/vast/
        - Section 2.4.3.4: Wrapper Resolution
    """
```

## Testing

### Test Requirements

- **Coverage**: Aim for >85% coverage
- **Unit Tests**: Test individual functions/methods (fast, run by pre-commit)
- **Integration Tests**: Test end-to-end workflows (slow, run in CI only)
- **IAB Examples**: Use official spec examples

### Test Structure

```python
import pytest
from xsp.protocols.vast import VastUpstream

@pytest.mark.asyncio
async def test_vast_wrapper_resolution():
    """Test VAST wrapper resolution per VAST 4.2 spec."""
    upstream = VastUpstream(
        endpoint="https://example.com/wrapper",
        max_wrapper_depth=3
    )
    
    result = await upstream.fetch()
    
    assert result.is_inline
    assert result.wrapper_depth <= 3
```

### Running Tests

```bash
# Pre-commit runs unit tests automatically on commit!

# Manual testing:

# All tests
pytest

# Specific file
pytest tests/unit/protocols/test_vast.py

# Specific test
pytest tests/unit/protocols/test_vast.py::test_vast_wrapper_resolution

# With coverage
pytest --cov=xsp --cov-report=html

# Skip network tests
pytest -m "not network"
```

## Documentation

### Types of Documentation

1. **Code Comments**: Explain complex logic
2. **Docstrings**: API documentation (required for all public APIs)
3. **README**: Project overview and quick start
4. **Guides**: How-to guides in `docs/`
5. **Examples**: Working code in `examples/`

### Documentation Updates

When changing code, update:
- Docstrings for modified functions/classes
- README if API changes
- Relevant guides in `docs/`
- CHANGELOG for notable changes

## Working with Copilot

### For Human Contributors

If you see a Copilot-generated PR:
- Review it like any other PR
- Provide feedback via comments
- Tag `@copilot` to request changes
- Copilot will iterate based on feedback

### Copilot Task Template

For tasks suitable for Copilot:
1. Use the **🤖 Copilot Task** template
2. Provide clear acceptance criteria
3. List specific files to modify
4. Include specification references
5. Specify quality requirements

### Delegating to Agents

Complex tasks can be delegated to specialized agents:
- `@orchestrator` - Planning and coordination
- `@developer` - Code implementation
- `@tester` - Testing
- `@doc-writer` - Documentation

Example:
```
@orchestrator Please create an implementation plan for OpenRTB 2.6 support
```

## Quality Checklist

Before submitting your PR:

### ✅ Automated by Pre-commit Hooks
- [ ] **Pre-commit installed**: `pre-commit install` (required!)
- [ ] Auto-formatting applied: `ruff format` ✅
- [ ] Lint issues fixed: `ruff check --fix` ✅
- [ ] Type checking passed: `mypy --strict` ✅
- [ ] Unit tests passed: `pytest tests/unit/` ✅
- [ ] Whitespace/YAML/TOML validated ✅

**Note**: Items with ✅ are automatically checked/fixed on every `git commit`!

### 📋 Manual Checklist
- [ ] Coverage maintained/improved (`pytest --cov`)
- [ ] Integration tests pass (if applicable)
- [ ] Documentation updated (docstrings, guides)
- [ ] CHANGELOG updated (for notable changes)
- [ ] Commit messages follow conventions
- [ ] PR template filled out completely

## Getting Help

- **Pre-commit Guide**: [.github/hooks/README.md](.github/hooks/README.md)
- **Documentation**: https://xsp-lib.readthedocs.io
- **Discussions**: https://github.com/pv-udpv/xsp-lib/discussions
- **Issues**: https://github.com/pv-udpv/xsp-lib/issues

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Mentioned in relevant documentation

Thank you for contributing to xsp-lib! 🎉
