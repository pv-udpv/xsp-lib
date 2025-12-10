# Naming Conventions

This document defines naming conventions for issues, pull requests, branches, and commits in the xsp-lib repository.

## Issue Naming Conventions

### Format

```
[Type] [Scope]: Brief description (#ParentIssue if applicable)
```

### Type Prefixes

| Type | Prefix | Description | Example |
|------|--------|-------------|---------|
| Bug | `🐛` or `[Bug]` | Bug fixes | `🐛 [VAST]: Wrapper resolution timeout` |
| Feature | `✨` or `[Feature]` | New features | `✨ [OpenRTB]: Add bid validation` |
| Protocol | `🔌` or `[Protocol]` | Protocol implementation | `🔌 Implement OpenRTB 2.6` |
| Documentation | `📝` or `[Docs]` | Documentation | `📝 [API]: Update VAST examples` |
| Task | `📋` or `[Task]` | General tasks | `📋 [Core]: Refactor transport layer` |
| Epic | `🎯` or `[Epic]` | Large initiatives | `🎯 OpenRTB 2.6 Implementation` |
| Subtask | `└─` or `[Subtask]` | Child of another issue | `└─ [OpenRTB]: Implement bid request (#15)` |

### Scope Guidelines

Scopes should match the module structure:

- `[Core]` - Core abstractions (BaseUpstream, Transport)
- `[VAST]` - VAST protocol
- `[OpenRTB]` - OpenRTB protocol
- `[DAAST]` - DAAST protocol (deprecated)
- `[Middleware]` - Middleware components
- `[Transport]` - Transport implementations
- `[CI]` - CI/CD and workflows
- `[Docs]` - Documentation
- `[Tests]` - Testing infrastructure

### Parent-Child Relationships

**Epic (Top-Level Issue):**
```
🎯 OpenRTB 2.6 Implementation
```

**Child Issues (Reference Parent):**
```
└─ [OpenRTB]: Implement bid request types (#15)
└─ [OpenRTB]: Implement bid response parsing (#15)
└─ [OpenRTB]: Add validation logic (#15)
└─ [Tests]: OpenRTB integration tests (#15)
```

**Continuous Process Issues:**
```
🔄 [CI]: Monthly dependency updates - 2025-01
🔄 [Docs]: Weekly documentation review - Week 50
```

### Examples

**Top-Level (Epic):**
- `🎯 VAST 4.2 Protocol Implementation`
- `🎯 Middleware System Enhancement`
- `🎯 OpenRTB 2.6 Support`

**Child Issues:**
- `└─ [VAST]: Implement wrapper resolution (#10)`
- `└─ [VAST]: Add macro substitution (#10)`
- `└─ [Tests]: VAST integration tests (#10)`

**Standalone Issues:**
- `🐛 [VAST]: Timeout error in wrapper resolution`
- `✨ [Core]: Add connection pooling to HTTP transport`
- `📝 [Docs]: Update getting started guide`

**Continuous Process:**
- `🔄 [CI]: Dependency update - December 2025`
- `🔄 [Security]: Monthly security audit - 2025-12`

## Pull Request Naming Conventions

### Format

```
type(scope): brief description (#IssueNumber)
```

### Type Prefixes

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(vast): add wrapper resolution (#10)` |
| `fix` | Bug fix | `fix(openrtb): correct bid validation (#23)` |
| `docs` | Documentation | `docs(api): update VAST examples (#45)` |
| `test` | Tests | `test(vast): add macro substitution tests (#10)` |
| `refactor` | Code refactoring | `refactor(core): simplify transport abstraction (#67)` |
| `perf` | Performance | `perf(vast): optimize XML parsing (#89)` |
| `chore` | Maintenance | `chore(ci): update GitHub Actions workflow` |
| `style` | Code style | `style: format with ruff` |
| `build` | Build system | `build: update dependencies` |
| `ci` | CI/CD | `ci: add code coverage reporting` |
| `revert` | Revert change | `revert: "feat(vast): add wrapper resolution"` |

### Multi-Scope PRs

For PRs affecting multiple scopes:

```
feat(vast,openrtb): add shared validation logic (#12)
```

### Parent Issue Reference

**Always include the issue number:**
```
feat(vast): implement wrapper resolution (#10)
└─ References parent epic: #5
```

### Examples

**Feature PRs:**
- `feat(vast): implement wrapper resolution with max depth (#10)`
- `feat(openrtb): add bid request validation (#15)`

**Bug Fix PRs:**
- `fix(vast): resolve timeout in wrapper resolution (#23)`
- `fix(core): handle connection errors in HTTP transport (#45)`

**Child PRs (Part of Epic):**
- `feat(openrtb): implement bid request types (#15) [Epic: #5]`
- `feat(openrtb): implement bid response parsing (#16) [Epic: #5]`

**Documentation PRs:**
- `docs(vast): add wrapper resolution examples (#67)`
- `docs(readme): update installation instructions (#89)`

## Branch Naming Conventions

### Format

```
type/scope/brief-description-issue-number
```

### Examples

**Feature Branches:**
```
feature/vast/wrapper-resolution-10
feature/openrtb/bid-validation-15
```

**Bug Fix Branches:**
```
fix/vast/timeout-error-23
fix/core/connection-handling-45
```

**Child Branches (Epic):**
```
feature/openrtb/bid-request-types-15-epic-5
feature/openrtb/bid-response-parsing-16-epic-5
```

**Copilot Branches:**
```
copilot/vast/wrapper-resolution-10
copilot/openrtb/bid-validation-15
```

**Epic Branches (Long-lived):**
```
epic/openrtb-2.6-implementation-5
epic/vast-4.2-support-10
```

## Commit Message Conventions

### Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body (optional)

footer (optional)
```

### Examples

**Simple Commits:**
```
feat(vast): add max_wrapper_depth parameter
fix(openrtb): correct bid validation logic
docs(api): update VastUpstream docstrings
test(vast): add wrapper resolution tests
```

**With Body:**
```
feat(vast): implement wrapper resolution with max depth

- Add max_wrapper_depth parameter to VastUpstream
- Track current depth during resolution
- Raise VastError when max depth exceeded
- Per VAST 4.2 §2.4.3.4

Fixes #10
```

**Breaking Changes:**
```
feat(core)!: change BaseUpstream interface

BREAKING CHANGE: The fetch() method now requires a timeout parameter.

Migration:
- Before: await upstream.fetch()
- After: await upstream.fetch(timeout=30.0)

Fixes #67
```

**Multi-Issue Commits:**
```
fix(vast,openrtb): handle empty response correctly

- VAST: Return None for empty XML
- OpenRTB: Return empty dict for empty JSON

Fixes #23, #45
```

## Labels

### Issue Labels

**Type Labels:**
- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements or additions to documentation
- `protocol` - Protocol implementation
- `epic` - Large multi-issue initiative
- `subtask` - Part of a larger issue

**Status Labels:**
- `needs-triage` - Needs initial review
- `ready` - Ready to be worked on
- `in-progress` - Currently being worked on
- `blocked` - Blocked by another issue
- `needs-review` - Needs code review

**Priority Labels:**
- `priority: critical` - Critical issue
- `priority: high` - High priority
- `priority: medium` - Medium priority
- `priority: low` - Low priority

**Area Labels:**
- `area: core` - Core abstractions
- `area: vast` - VAST protocol
- `area: openrtb` - OpenRTB protocol
- `area: middleware` - Middleware
- `area: ci` - CI/CD
- `area: docs` - Documentation

**Special Labels:**
- `copilot-task` - Suitable for Copilot
- `good-first-issue` - Good for newcomers
- `help-wanted` - Extra attention needed

### Label Hierarchy for Epics

**Epic Issue:**
```
Labels: epic, area: openrtb, priority: high
```

**Child Issues:**
```
Labels: subtask, area: openrtb, parent: #5
```

## Examples of Complete Workflows

### Example 1: Simple Bug Fix

**Issue:**
```
Title: 🐛 [VAST]: Timeout error in wrapper resolution
Labels: bug, area: vast, priority: high
```

**Branch:**
```
fix/vast/timeout-error-23
```

**Commits:**
```
fix(vast): add timeout parameter to wrapper resolution
test(vast): add timeout test cases
docs(vast): document timeout parameter
```

**PR:**
```
Title: fix(vast): resolve timeout in wrapper resolution (#23)
Labels: bug, area: vast
```

### Example 2: Epic with Multiple Children

**Epic Issue:**
```
Title: 🎯 OpenRTB 2.6 Implementation
Number: #5
Labels: epic, area: openrtb, priority: critical
Description: 
  Implement full OpenRTB 2.6 protocol support
  
  Child Issues:
  - [ ] #15 - Bid request types
  - [ ] #16 - Bid response parsing
  - [ ] #17 - Validation logic
  - [ ] #18 - Integration tests
```

**Child Issue 1:**
```
Title: └─ [OpenRTB]: Implement bid request types (#5)
Number: #15
Labels: subtask, area: openrtb, parent: #5
```

**Branch for Child 1:**
```
feature/openrtb/bid-request-types-15-epic-5
```

**PR for Child 1:**
```
Title: feat(openrtb): implement bid request types (#15) [Epic: #5]
Labels: enhancement, area: openrtb
```

### Example 3: Continuous Process

**Monthly Issue:**
```
Title: 🔄 [CI]: Dependency updates - December 2025
Labels: maintenance, area: ci, recurring
```

**Branch:**
```
chore/ci/dependency-updates-dec-2025
```

**PR:**
```
Title: chore(deps): update dependencies for December 2025
```

## Visual Hierarchy Indicators

### In Issue Lists

Use Unicode characters for visual hierarchy:

```
🎯 OpenRTB 2.6 Implementation (#5)
  └─ [OpenRTB]: Implement bid request types (#15)
  └─ [OpenRTB]: Implement bid response parsing (#16)
  └─ [Tests]: OpenRTB integration tests (#17)
```

### In PR Titles

Reference parent in square brackets:

```
feat(openrtb): implement bid request types (#15) [Epic: #5]
feat(openrtb): implement bid response parsing (#16) [Epic: #5]
```

### In Commit Messages

Reference both child and parent:

```
feat(openrtb): add BidRequest dataclass

Part of #15 (Epic: #5)
```

## Automation

### GitHub Actions

Use labels to trigger automation:

- `copilot-task` + assignment → Copilot starts work
- `epic` → Create project board
- `subtask` → Link to parent issue
- `needs-triage` → Notify maintainers

### Label Inheritance

Child issues inherit some labels from parent:
- Area labels (`area: *`)
- Priority labels (if not explicitly set)

## Best Practices

1. **Always reference parent issues** in titles using `(#ParentNumber)`
2. **Use visual hierarchy** with `└─` for child issues
3. **Keep titles concise** - details go in the description
4. **Use consistent scopes** - match module structure
5. **Label appropriately** - helps with filtering and automation
6. **Include issue numbers** in PR titles and commits
7. **Use emojis** for visual scanning (optional but helpful)

## Quick Reference

### Issue Title Format
```
[Type] [Scope]: Description (#Parent)
```

### PR Title Format
```
type(scope): description (#Issue) [Epic: #Parent]
```

### Branch Name Format
```
type/scope/description-issue-parent
```

### Commit Message Format
```
type(scope): subject

Part of #Issue (Epic: #Parent)
```
