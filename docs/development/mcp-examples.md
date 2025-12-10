# MCP Integration Examples

This guide provides practical examples of using GitHub Copilot's Model Context Protocol (MCP) integration with xsp-lib custom agents.

## Example 1: Protocol Implementation with Spec Access

### Scenario
You need to implement VAST 4.2 wrapper resolution with proper depth tracking.

### Without MCP
```bash
@developer Implement VAST wrapper resolution
```
- Agent would implement based on general knowledge
- May miss specification details
- Requires manual spec verification

### With MCP
```bash
@developer Implement VAST wrapper resolution per VAST 4.2 section 2.4.3.4 with max depth of 5 wrappers
```

**What happens:**
1. **Web Server**: Fetches VAST 4.2 spec from iabtechlab.com
2. **Filesystem Server**: Reads existing VAST implementation
3. **GitHub Server**: Checks for related issues about wrapper resolution
4. **Python Server**: Validates code with type checking
5. **Memory Server**: Stores context about implementation decisions

**Result**: Implementation that precisely follows VAST 4.2 specification with proper error handling and depth tracking.

---

## Example 2: Test Generation with Protocol Validation

### Scenario
Create comprehensive tests for OpenRTB bid validation.

### With MCP
```bash
@tester Create tests for OpenRTB 2.6 bid validation covering all required fields from section 3.2.1
```

**What happens:**
1. **Web Server**: Fetches OpenRTB 2.6 specification section 3.2.1
2. **Filesystem Server**: Reads existing test structure and fixtures
3. **Python Server**: Runs generated tests to verify they work
4. **Memory Server**: Stores test patterns for future reference

**Generated Tests Include:**
- All required fields validation
- Type checking for each field
- Edge cases (empty, null, invalid values)
- Parametrized tests for field combinations
- Async test patterns

**Example Output:**
```python
import pytest
from xsp.protocols.openrtb import BidRequest

@pytest.mark.parametrize("missing_field", ["id", "imp", "site", "device"])
async def test_bid_request_missing_required_field(missing_field):
    """Test that BidRequest raises error when required field is missing."""
    data = {
        "id": "123",
        "imp": [{"id": "1"}],
        "site": {"id": "site1"},
        "device": {"ua": "Mozilla/5.0"}
    }
    del data[missing_field]
    
    with pytest.raises(ValueError, match=f"Missing required field: {missing_field}"):
        BidRequest.from_dict(data)
```

---

## Example 3: Documentation with Accurate References

### Scenario
Document the VAST upstream configuration options.

### With MCP
```bash
@doc-writer Document VastUpstream configuration with all parameters and spec references
```

**What happens:**
1. **Filesystem Server**: Reads VastUpstream implementation
2. **Web Server**: Fetches relevant VAST specification sections
3. **GitHub Server**: Checks existing documentation patterns
4. **Memory Server**: Recalls documentation style preferences

**Generated Documentation Includes:**
- Complete parameter list with types
- Default values and valid ranges
- IAB specification references with section numbers
- Working code examples
- Common pitfalls and best practices

**Example Output:**
```markdown
# VAST Upstream Configuration

## VastUpstream Parameters

### version
- **Type**: `VastVersion` (enum)
- **Default**: `VastVersion.V4_2`
- **Valid Values**: `V3_0`, `V4_0`, `V4_1`, `V4_2`
- **Spec Reference**: VAST 4.2 §2.1 - Version Attribute

Specifies the VAST version to use for ad requests and response parsing.

**Example:**
\`\`\`python
from xsp.protocols.vast import VastUpstream, VastVersion

upstream = VastUpstream(
    endpoint="https://ad-server.com/vast",
    version=VastVersion.V4_2  # Use VAST 4.2
)
\`\`\`

### max_wrapper_depth
- **Type**: `int`
- **Default**: `5`
- **Valid Range**: 1-10
- **Spec Reference**: VAST 4.2 §2.4.3.4 - Wrapper Resolution

Maximum number of wrapper redirects to follow before stopping.
Per VAST 4.2 spec, video players should support at least 5 wrapper redirects.
```

---

## Example 4: Complex Feature Planning

### Scenario
Plan implementation of frequency capping feature.

### With MCP
```bash
@orchestrator Plan implementation of frequency capping with Redis backend and per-user limits
```

**What happens:**
1. **GitHub Server**: Checks for existing frequency capping issues
2. **Filesystem Server**: Analyzes current session management code
3. **Memory Server**: Recalls project architecture decisions
4. **Web Server**: Looks up frequency capping best practices

**Generated Plan:**
```markdown
# Frequency Capping Implementation Plan

## Phase 1: Core Abstractions (3-4 hours)
- [ ] Create `FrequencyCapConfig` dataclass
- [ ] Define `FrequencyCapper` protocol
- [ ] Implement `InMemoryFrequencyCapper` for testing
- [ ] Add tests for core abstractions

## Phase 2: Redis Backend (4-5 hours)
- [ ] Create `RedisFrequencyCapper` implementation
- [ ] Add Redis connection management
- [ ] Implement atomic increment operations
- [ ] Add TTL support for time-based caps
- [ ] Add tests with redis-py fixtures

## Phase 3: Session Integration (2-3 hours)
- [ ] Integrate with `UpstreamSession`
- [ ] Add `check_frequency_cap()` method
- [ ] Handle cap exceeded scenarios
- [ ] Update session tests

## Phase 4: Documentation (1-2 hours)
- [ ] Document FrequencyCapper protocol
- [ ] Create usage guide with examples
- [ ] Add Redis setup instructions
- [ ] Document configuration options

Total Effort: 10-14 hours
Dependencies: Requires SessionContext (PR #67)
```

---

## Example 5: Bug Fix with Context

### Scenario
Fix a bug in VAST macro substitution for special characters.

### With MCP
```bash
@developer Fix VAST macro substitution bug when URL contains Cyrillic characters (issue #123)
```

**What happens:**
1. **GitHub Server**: Fetches issue #123 details and comments
2. **Filesystem Server**: Locates macro substitution code
3. **Web Server**: Checks VAST spec for URL encoding requirements
4. **Python Server**: Runs existing tests to verify the bug
5. **Memory Server**: Stores the fix approach for similar issues

**Fix Process:**
1. Agent reads issue description and reproduction steps
2. Fetches VAST 4.2 specification section on URL encoding
3. Analyzes current macro substitution implementation
4. Identifies the encoding bug
5. Implements fix with proper URL encoding
6. Adds test case for Cyrillic characters
7. Runs full test suite to ensure no regressions

**Generated Fix:**
```python
def substitute_macros(template: str, values: dict[str, str]) -> str:
    """Substitute VAST macros in template string.
    
    Handles URL encoding per VAST 4.2 §3.3.1.
    """
    result = template
    for macro, value in values.items():
        # URL encode the value to handle special characters
        encoded_value = urllib.parse.quote(value, safe='')
        result = result.replace(f"[{macro}]", encoded_value)
    return result
```

**Generated Test:**
```python
def test_substitute_macros_cyrillic():
    """Test macro substitution with Cyrillic characters."""
    template = "https://example.com?url=[PAGEURL]"
    values = {"PAGEURL": "https://сайт.рф/страница"}
    
    result = substitute_macros(template, values)
    
    # Should be URL-encoded
    assert "https://example.com?url=https%3A%2F%2F" in result
    assert "сайт" not in result  # Cyrillic should be encoded
```

---

## Example 6: Cross-Agent Coordination

### Scenario
Implement a new OpenRTB feature end-to-end.

### With MCP
```bash
@orchestrator Implement OpenRTB 2.6 device extension support with code, tests, and documentation
```

**What happens (orchestrated workflow):**

### Step 1: Planning (@orchestrator)
```markdown
Plan:
1. @developer: Implement device extension models
2. @developer: Add parsing logic
3. @tester: Create comprehensive tests
4. @doc-writer: Document the feature

Estimated: 8-10 hours total
```

### Step 2: Implementation (@developer)
```bash
@developer Implement OpenRTB 2.6 device extension per section 3.2.18
```
- Fetches OpenRTB 2.6 spec
- Creates DeviceExt model
- Adds parsing logic
- Validates with mypy

### Step 3: Testing (@tester)
```bash
@tester Create tests for OpenRTB device extension covering all fields
```
- Reads the implementation
- Fetches spec for test cases
- Generates unit tests
- Creates fixtures

### Step 4: Documentation (@doc-writer)
```bash
@doc-writer Document device extension with examples and spec references
```
- Reads implementation
- Fetches spec details
- Creates documentation
- Adds code examples

### Step 5: Review (@orchestrator)
```bash
@orchestrator Review device extension implementation completeness
```
- Checks all deliverables
- Verifies tests pass
- Validates documentation
- Confirms spec compliance

---

## Example 7: Using Memory Across Sessions

### Scenario
Working on a multi-day feature with context preservation.

### Day 1
```bash
@orchestrator I'm starting work on Phase 2: Protocol handlers. 
We need to implement ProtocolHandler ABC and refactor fetch→request terminology.
```

**Memory stored:**
- Current phase: Phase 2
- Goal: ProtocolHandler ABC + terminology refactor
- Context: Working on protocol abstraction layer

### Day 2 (New Session)
```bash
@orchestrator What's the status of Phase 2?
```

**Memory recalled:**
- Phase 2 in progress
- ProtocolHandler ABC task
- Terminology refactor pending

**Response:**
```markdown
Based on stored context:

Phase 2: Protocol Handlers (In Progress)

Completed:
- None yet (just started yesterday)

In Progress:
- ProtocolHandler ABC design
- fetch→request terminology refactor

Next Steps:
1. Finalize ProtocolHandler ABC interface
2. Create AdRequest/AdResponse schemas
3. Refactor existing upstreams
4. Update tests
5. Update documentation

Would you like to continue with ProtocolHandler ABC?
```

---

## Example 8: Performance Optimization

### Scenario
Optimize async performance of VAST wrapper resolution.

### With MCP
```bash
@developer Optimize VAST wrapper resolution for parallel fetching while maintaining spec compliance
```

**What happens:**
1. **Filesystem Server**: Reads current wrapper resolution code
2. **Web Server**: Checks VAST 4.2 spec for parallel fetching rules
3. **Python Server**: Profiles current performance
4. **Memory Server**: Stores optimization strategies

**Analysis:**
- Current: Sequential wrapper fetching (5 wrappers = 5 sequential requests)
- Spec allows: Parallel fetching of ad pods
- Optimization: Use `asyncio.gather()` for parallel wrapper resolution

**Generated Optimization:**
```python
async def resolve_wrappers(
    self,
    vast_url: str,
    max_depth: int = 5
) -> list[VastAd]:
    """Resolve VAST wrappers with parallel fetching.
    
    Per VAST 4.2 §2.4.3.4, wrappers can be resolved in parallel
    for ad pods while maintaining sequence for single ad wrappers.
    """
    wrappers = []
    current_depth = 0
    
    while current_depth < max_depth:
        vast = await self.fetch_vast(vast_url)
        
        if vast.has_inline_ads():
            return wrappers + vast.inline_ads
            
        # Parallel fetch of multiple wrapper URLs (ad pods)
        wrapper_urls = vast.get_wrapper_urls()
        if not wrapper_urls:
            break
            
        # Fetch all wrappers in parallel
        wrapper_tasks = [
            self.fetch_vast(url) for url in wrapper_urls
        ]
        wrapper_responses = await asyncio.gather(*wrapper_tasks)
        
        wrappers.extend(wrapper_responses)
        current_depth += 1
    
    return wrappers
```

---

## Best Practices

### 1. Be Specific with Spec References
```bash
# ✅ Good
@developer Implement VAST extension per VAST 4.2 section 2.4.5.1

# ❌ Less effective
@developer Add VAST extension support
```

### 2. Reference Related Issues
```bash
# ✅ Good
@developer Fix macro substitution encoding bug (issue #123) per VAST 4.2 §3.3.1

# ❌ Less effective
@developer Fix the encoding bug
```

### 3. Use Orchestrator for Complex Tasks
```bash
# ✅ Good for complex work
@orchestrator Implement frequency capping end-to-end

# ✅ Good for simple work
@developer Add frequency cap check method
```

### 4. Leverage Memory for Context
```bash
# First: Set context
@orchestrator I'm implementing feature X following approach Y

# Later: Reference context
@orchestrator Continue with feature X next step
```

---

## Troubleshooting MCP

### MCP Not Working
**Check:**
```bash
# Verify Node.js
node --version  # Should be v16+

# Test MCP server
npx -y @modelcontextprotocol/server-filesystem --help

# Verify MCP config
python -m json.tool < .github/copilot/mcp.json
```

### Specs Not Accessible
**Check:**
```bash
# Test internet access
curl -I https://iabtechlab.com

# Verify allowed domains in mcp.json
cat .github/copilot/mcp.json | grep -A 10 allowedDomains
```

### Agent Not Using MCP
**Ensure:**
- Using GitHub Copilot Chat (not inline completions)
- Repository is open in IDE
- MCP configuration exists in `.github/copilot/mcp.json`
- Using agent mentions (e.g., `@developer`)

---

## Example 9: Code Refactoring with Rope

### Scenario
Refactor existing VAST parsing code to improve maintainability.

### With MCP (Rope Refactoring)
```bash
@developer Refactor the VastParser class to extract the XML validation logic into a separate method
```

**What happens:**
1. **Filesystem Server**: Reads the current VastParser implementation
2. **Rope-Refactor Server**: Analyzes code structure and dependencies
3. **Python Server**: Validates the refactored code with type checking
4. **Rope-Refactor Server**: Performs safe extract method refactoring

**Refactoring Operations Available:**
- **Rename**: Safely rename variables, functions, classes across the codebase
- **Extract Method**: Pull code blocks into new methods
- **Extract Variable**: Create variables for complex expressions
- **Inline**: Inline method/variable definitions
- **Organize Imports**: Sort and optimize import statements

**Example Output:**
```python
# Before
class VastParser:
    def parse(self, xml_string: str) -> VastAd:
        # Validate XML structure
        if not xml_string.startswith('<?xml'):
            raise ValueError("Invalid XML")
        # Parse XML
        tree = ET.fromstring(xml_string)
        # More parsing logic...
        return ad

# After (with extract method)
class VastParser:
    def _validate_xml_structure(self, xml_string: str) -> None:
        """Validate XML structure before parsing."""
        if not xml_string.startswith('<?xml'):
            raise ValueError("Invalid XML")
    
    def parse(self, xml_string: str) -> VastAd:
        self._validate_xml_structure(xml_string)
        tree = ET.fromstring(xml_string)
        # More parsing logic...
        return ad
```

**Benefits:**
- Safe refactoring with dependency analysis
- Maintains type hints and docstrings
- Updates all references automatically
- Preserves code functionality

---

## Additional Resources

- [MCP Integration Guide](mcp-integration.md)
- [Custom Agents Documentation](../../AGENTS.md)
- [GitHub Copilot MCP Docs](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/extend-coding-agent-with-mcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Python Rope Documentation](https://github.com/python-rope/rope)

---

**Last Updated**: December 10, 2025
**Version**: 1.1
