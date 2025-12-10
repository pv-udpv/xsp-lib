# Architecture Decision Log

**Date:** December 10, 2025  
**Status:** Active  
**Repository:** pv-udpv/xsp-lib  

---

## Summary of Recent Decisions

### Decision 1: Close PR #61 (EmbedHttpClient Refactoring)

**Status:** ❌ CLOSED - Superseded by PR #63  
**Date:** December 10, 2025  
**Impact:** No impact to ongoing work (was just planning, no code changes)

#### Rationale

PR #61 proposed refactoring EmbedHttpClient to separate concerns:
- Domain-specific configuration (UpstreamConfig)
- HTTP implementation details (HttpClientConfig)
- Three-layer architecture pattern

**This exact work is already complete in PR #63**, which provides:
- ✅ UpstreamConfig dataclass (src/xsp/core/config.py)
- ✅ Transport-agnostic configuration
- ✅ merge_params() and merge_headers() methods
- ✅ Integration with BaseUpstream
- ✅ 13+ unit tests
- ✅ Full documentation

#### Decision

**CLOSE PR #61** with explanation:

> The configuration architecture proposed in this PR was already implemented and merged as PR #63. That PR provides:
>
> - UpstreamConfig dataclass with transport-agnostic design
> - Separation of concerns (config vs transport)
> - merge_params() and merge_headers() helpers
> - Full test coverage and documentation
>
> This PR would duplicate that work. Future enhancements (YAML config, HttpClientConfig dataclass) should be separate PRs.
>
> Closing as superseded by #63.

---

### Decision 2: Defer PR #60 (TOML Validation) to After Phase 1

**Status:** ⏳ DEFERRED  
**Date:** December 10, 2025  
**Impact:** Blocks nothing (optional enhancement)

#### Rationale

PR #60 adds TOML syntax validation to ConfigGenerator using tomlkit:
- Quality implementation
- 14 comprehensive tests
- Optional feature (not core library)

**Why defer:**

1. **Not on critical path** - Doesn't enable any required features
2. **Optional feature** - Configuration validation is nice-to-have
3. **New dependencies** - Adds tomlkit to optional dependencies
4. **Can be added anytime** - No cascading effects

#### Decision

**DEFER UNTIL AFTER PHASE 1** (mid-January 2025)

Rationale:
- Focus Phase 1 on core abstractions (Session, Config system)
- TOML validation is secondary concern
- Can be merged after SessionContext/UpstreamSession/Configurable complete
- Will provide better value once configuration system is mature

---

### Decision 3: Block PR #65 (Breaking Changes) Until Phase 2 Complete

**Status:** ⚠️ BLOCKED  
**Date:** December 10, 2025  
**Action:** Close or convert to issue planning document

#### Rationale

PR #65 proposes massive breaking changes:
- Rename upstream.fetch() → upstream.request()
- Rename transport.send() → transport.request()
- "Correct terminology"

**Why this conflicts:**

1. **SessionContext already defines request()** (PR #57)
   - Would cause name collision
   - UpstreamSession protocol uses request()

2. **Would break 4 merged PRs:**
   - PR #64 (HTTP Transport) - uses fetch()
   - PR #63 (UpstreamConfig) - depends on fetch() signature
   - PR #62 (Orchestrator) - expects current API
   - PR #58 (Version macros) - expects Transport.send()

3. **Breaking changes should be Phase 2, not Phase 1**
   - Violates "Foundation" phase discipline
   - Should be part of deliberate "Protocol Handlers" refactoring
   - Not urgent (current terminology works)

#### Decision

**CLOSE PR #65 with explanation:**

> This PR proposes breaking API changes that conflict with:
> - SessionContext.request() from PR #57
> - Current architecture merged in PRs #58, #62, #63, #64
>
> Terminology refactoring is important, but should be:
> - Part of Phase 2: Protocol Handlers (Issue #40)
> - Planned alongside other breaking changes
> - Coordinated with full API redesign
>
> Phase 1 focuses on foundation (Session, Config). Phase 2 (Terminology) comes next.
> Current terminology works well enough for Phase 1.
>
> Closing. This work will be revisited in Phase 2 planning.

---

### Decision 4: Focus Phase 1 on Session Management + Config System

**Status:** ✅ APPROVED  
**Date:** December 10, 2025  
**Impact:** Clear Phase 1 scope

#### Rationale

Phase 1 (Foundation) should focus on core abstractions:

1. **SessionContext** (Issue #37)
   - Immutable session context for ad serving
   - Shared across wrapper resolution chain
   - Foundation for stateful features

2. **UpstreamSession Protocol** (Issue #37)
   - Stateful session for frequency capping + budget tracking
   - Integrates with SessionContext
   - Foundation for Phase 4 production features

3. **@configurable Decorator** (Issue #15)
   - Explicit configuration system
   - Registry-based configuration discovery
   - Enables TOML template generation

4. **Documentation** (Issues #35, #36)
   - Architecture document
   - Session management guide
   - Configuration guide

#### Decision

**PHASE 1 SCOPE IS LOCKED:**

- SessionContext + UpstreamSession (Issue #37) ✓
- @configurable decorator (Issue #15) ✓
- Architecture documentation (Issue #35) ✓
- Session management guide (Issue #36) ✓
- No breaking changes
- No major refactoring
- Foundation-only work

**Phase 1 Completion:** 2-3 weeks (target: Dec 23 - Jan 6)

---

## Current Architecture State

### Core Abstractions (Stable)

```
Upstream[T] Protocol
    │
    └─ BaseUpstream[T] Implementation
        ├─ Transport abstraction
        ├─ Decoder
        └─ UpstreamConfig (from PR #63)

SessionContext (frozen dataclass) ─ Planned PR #67
UpstreamSession Protocol           ─ Planned PR #67
```

### Transport Implementations (Stable)

```
Transport Protocol
    ├─ HttpTransport (PR #58, #64) ✅
    ├─ FileTransport ✅
    └─ MemoryTransport ✅
```

### Protocol Implementations (In Progress)

```
VastUpstream (PR #58) ✅
    └─ ChainResolver (PR #59, PR #66) ✅

OpenRTB (Planned - Phase 2/3)
Daast (Planned - Phase 2/3)
Cats (Planned - Phase 2/3)
```

### Configuration System (Stable)

```
UpstreamConfig (PR #63) ✅
    └─ @configurable decorator (Planned PR #68)
        └─ ConfigGenerator (Planned PR #68)
            └─ TOML generation (Deferred)
            └─ YAML generation (Planned)
```

---

## PR Status Matrix

### Current Pull Requests

| # | Title | Status | Decision | Impact |
|---|-------|--------|----------|--------|
| #59 | VAST chain resolver | Draft | ✅ READY | Merge this week |
| #60 | TOML validation | Draft | ⏳ DEFER | Post-Phase 1 |
| #61 | EmbedHttpClient refactor | Draft | ❌ CLOSE | Superseded by #63 |
| #65 | Phase 2 terminology | Draft | ⚠️ BLOCK | Breaking changes |
| #67 | SessionContext (planned) | Pending | ✅ TODO | PR this week |
| #68 | @configurable (planned) | Pending | ✅ TODO | PR this week |

### Merged Pull Requests

| # | Title | Status | Quality |
|----|-------|--------|----------|
| #58 | HTTP transport + VAST fetch | ✅ Merged | ★★★★★ |
| #62 | Protocol-agnostic orchestrator | ✅ Merged | ★★★★★ |
| #63 | UpstreamConfig dataclass | ✅ Merged | ★★★★★ |
| #64 | HTTP transport + errors | ✅ Merged | ★★★★★ |

---

## Immediate Action Items

### This Week (Dec 10-16)

❌ **Close PR #61** (EmbedHttpClient refactor)
- Reason: Superseded by PR #63
- Time: 5 minutes
- Update: Add comment explaining decision

❌ **Close PR #65** (Terminology refactoring)
- Reason: Breaking changes should be Phase 2
- Time: 10 minutes
- Update: Convert to Issue #45 (Phase 2 Planning)

⏳ **Defer PR #60** (TOML validation)
- Reason: Optional enhancement, not critical
- Time: 5 minutes
- Action: Add label "deferred", target Phase 1 completion

✅ **Start Phase 1 Implementation**
- Task 1: SessionContext + UpstreamSession (PR #67)
  - Target: Dec 11-12
  - Effort: 3 hours

- Task 2: @configurable decorator (PR #68)
  - Target: Dec 12-13
  - Effort: 3 hours

- Task 3: Architecture documentation (PR #69)
  - Target: Dec 13-14
  - Effort: 4 hours

### Next Week (Dec 16-23)

✅ **Complete Phase 1**
- Task 4: Session management guide (PR #70)
  - Effort: 2 hours

- Task 5: Code review & merge Phase 1 PRs
  - Effort: 2 hours

- Task 6: Verification & testing
  - Effort: 1 hour

---

## Phase 1 Acceptance Criteria

### Code Quality

- ✅ SessionContext immutable (frozen=True)
- ✅ UpstreamSession protocol complete
- ✅ @configurable decorator working
- ✅ TOML generation from registry
- ✅ 95%+ code coverage on core/
- ✅ mypy --strict: 0 errors
- ✅ ruff lint: 0 errors
- ✅ 30+ tests passing

### Documentation

- ✅ Architecture document (3000+ words)
- ✅ Session management guide (1500+ words)
- ✅ Configuration guide (1000+ words)
- ✅ All examples working and tested
- ✅ Cross-references between docs

### Team Agreement

- ✅ All Phase 1 PRs reviewed and approved
- ✅ No open blockers
- ✅ Ready for Phase 2

---

## Phase 2 Planning (Preview)

**When:** After Phase 1 complete (estimated Jan 6)
**Duration:** 2-3 weeks
**Focus:** Protocol handlers and terminology refactoring

### Planned Work

1. **ProtocolHandler ABC** - Abstract interface for all protocols
2. **Terminology Refactoring** - fetch() → request(), send() → request()
3. **AdRequest/AdResponse Schemas** - TypedDict-based protocol messages
4. **Breaking Changes** - Coordinated API redesign

### Will Address

- Current PR #65 work (terminology changes)
- Protocol abstraction layer
- Type-safe request/response handling
- Extension patterns for custom fields

---

## Risk Assessment

### Low Risk

✅ **Closing PR #61:** No impact (was just planning, PR #63 already merged)
✅ **Deferring PR #60:** No impact (optional enhancement, not on critical path)
✅ **Blocking PR #65:** Low risk (better to defer breaking changes anyway)

### Medium Risk

⚠️ **Phase 1 scope creep:** Mitigated by locked scope document (this file)
⚠️ **Session implementation complexity:** Mitigated by clear protocol definition
⚠️ **Configuration registry design:** Mitigated by @configurable being proven pattern

### No Current Blockers

✅ All Phase 1 work can start immediately
✅ No architectural conflicts
✅ No dependency issues

---

## Architecture Going Forward

### Core Principles

1. **Foundation First** - Each phase builds on previous
2. **No Jumping Ahead** - Phase 2 after Phase 1 complete
3. **Clear Scope** - Each phase has locked deliverables
4. **Breaking Changes Coordinated** - Only in Phase 2+, planned together
5. **Backward Compatible** - Until v1.0.0

### Dependency Graph

```
Phase 1: Foundation
└── Session + Config

    │
    └── Phase 2: Protocol Handlers
         └── Terminology + Abstraction

             │
             └── Phase 3: Advanced
                  └── Orchestrator + State

                      │
                      └── Phase 4: Production
                           └── Frequency + Budget
```

### Timeline

```
Dec 10-23:  Phase 1 (3 weeks)
Jan 6-20:   Phase 2 (2-3 weeks)
Jan 20-Feb 10: Phase 3 (3-4 weeks)
Feb 10-24:  Phase 4 (2-3 weeks)
Feb 24-Mar 10: Testing & Stabilization (2 weeks)
```

---

## References

### Key Documents

- **IMPLEMENTATION_PLAN.md** - Full 4-phase roadmap
- **ARCHITECTURE.md** - Current system architecture
- **README.md** - Project overview

### Key Issues

- **#34** - Phase 1: Foundation (parent)
- **#35** - Architecture documentation
- **#36** - Session management guide
- **#37** - SessionContext + UpstreamSession
- **#40** - Phase 2: Protocol handlers
- **#42** - Phase 3: Advanced features
- **#44** - Phase 4: Production features

### Key PRs

**Merged:**
- #63 - UpstreamConfig dataclass
- #62 - Protocol-agnostic orchestrator
- #60 - TOML validation (deferred further enhancements)
- #58/64 - HTTP transport

**To Close/Defer:**
- #61 - Close (superseded)
- #65 - Close (blocking changes)
- #60 - Defer (optional)

---

## Approval & Sign-Off

**Document Owner:** @pv-udpv  
**Last Updated:** December 10, 2025  
**Status:** ACTIVE  
**Next Review:** December 17, 2025  

### Decisions Approved

- ✅ Close PR #61 (superseded)
- ✅ Defer PR #60 (optional)
- ✅ Block PR #65 (breaking changes)
- ✅ Phase 1 scope locked
- ✅ Implementation plan approved

---

**END OF ARCHITECTURE DECISION LOG**
