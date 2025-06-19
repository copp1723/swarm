# Architecture Decision Records

This document captures key architectural decisions made in the SWARM project.

## ADR-001: Web Framework Selection

**Date:** 2024-01-01  
**Status:** Accepted

### Context
We needed to choose a web framework for building the multi-agent chat system API.

### Decision
We chose Flask over FastAPI or Django.

### Rationale
- **Flask** provides the right balance of simplicity and flexibility
- Mature ecosystem with extensive middleware support
- Easy integration with both sync and async operations
- Lighter weight than Django for API-focused applications
- Team familiarity and existing codebase

### Consequences
- Need to add async support manually (solved with async_bridge)
- Must implement API documentation separately
- More flexibility in structuring the application

---

## ADR-002: Plugin Architecture

**Date:** 2024-01-10  
**Status:** Accepted

### Context
The system needed to be extensible without modifying core code.

### Decision
Implement a plugin system with hot-reload capability.

### Rationale
- **Extensibility** - Add features without touching core
- **Isolation** - Plugins can fail without crashing the system
- **Development Speed** - Hot-reload enables rapid iteration
- **Community** - Others can contribute plugins

### Implementation
- Plugins loaded from `plugins/` directory
- File watcher for automatic reloading
- Service registration in DI container
- Plugin lifecycle management

### Consequences
- Additional complexity in service management
- Need robust error handling for plugin failures
- Performance overhead of file watching (minimal)

---

## ADR-003: NLU Service Architecture

**Date:** 2024-01-15  
**Status:** Accepted

### Context
Needed intelligent task routing without hardcoded rules.

### Decision
Build a separate NLU service for intent recognition and entity extraction.

### Rationale
- **Separation of Concerns** - NLU logic isolated from business logic
- **Flexibility** - Easy to swap NLU implementations
- **Scalability** - Can scale NLU separately if needed
- **Accuracy** - Dedicated service for better intent detection

### Implementation
- Pattern-based intent recognition (12 intent types)
- Entity extraction for technical terms
- Confidence scoring for routing decisions
- Integration with orchestrator service

### Consequences
- Additional service to maintain
- Latency added to request processing (mitigated by caching)
- Need to maintain intent patterns

---

## ADR-004: Database Choice

**Date:** 2024-01-05  
**Status:** Accepted

### Context
Needed a database for storing tasks, audit logs, and chat history.

### Decision
Use SQLAlchemy with support for both SQLite (dev) and PostgreSQL (prod).

### Rationale
- **Flexibility** - Easy local development with SQLite
- **Production Ready** - PostgreSQL for production scale
- **ORM Benefits** - Type safety and migrations
- **Async Support** - SQLAlchemy 2.0 has excellent async support

### Implementation
- Centralized database configuration
- Connection pooling for performance
- Support for both sync and async operations
- Environment-based database selection

### Consequences
- Need to test with both databases
- Schema must work across both systems
- Connection pool tuning required for production

---

## ADR-005: Async/Sync Bridge

**Date:** 2024-01-20  
**Status:** Accepted

### Context
Mixed ecosystem with some async libraries and some sync-only APIs.

### Decision
Implement a unified async/sync bridge utility.

### Rationale
- **Compatibility** - Work with both async and sync libraries
- **Performance** - Cached thread pool executors
- **Simplicity** - Single pattern for all conversions
- **Safety** - Proper event loop detection

### Implementation
```python
from utils.async_bridge import AsyncBridge

bridge = AsyncBridge()
# Convert async to sync
result = bridge.run_async(async_func())
# Convert sync to async  
result = await bridge.run_sync(sync_func)
```

### Consequences
- Small performance overhead for conversions
- Need to be careful about blocking operations
- Thread pool size needs tuning

---

## ADR-006: Security Architecture

**Date:** 2024-02-01  
**Status:** Accepted

### Context
Need comprehensive security without impacting development velocity.

### Decision
Implement security through middleware and utilities.

### Rationale
- **Automatic Protection** - Security headers on all responses
- **Developer Friendly** - Security by default
- **Flexible** - Different policies for dev/prod
- **Comprehensive** - Covers OWASP top 10

### Implementation
- Security headers middleware
- CSP policies per environment
- Centralized input validation
- Path traversal protection
- Updated dependencies

### Consequences
- Slightly stricter development environment
- Need to maintain CSP policies
- Regular security updates required

---

## ADR-007: Dependency Injection Pattern

**Date:** 2024-01-08  
**Status:** Revised

### Context
Need to manage service dependencies cleanly.

### Original Decision
Use full-featured DI container with complex scoping.

### Revised Decision
Simplify to basic singleton/transient pattern.

### Rationale
- **Simplicity** - Original was over-engineered
- **Performance** - Less overhead
- **Debugging** - Easier to trace issues
- **Sufficient** - Covers all actual use cases

### Implementation
```python
# Simple DI with dataclasses
@dataclass
class ServiceConfig:
    service_type: Type
    lifetime: Literal['singleton', 'transient']
    factory: Optional[Callable] = None
```

### Consequences
- Lost some advanced features (not used anyway)
- Much simpler codebase
- Better performance
- Easier onboarding

---

## ADR-008: Monitoring Strategy

**Date:** 2024-01-25  
**Status:** Accepted

### Context
Need visibility into system performance and agent behavior.

### Decision
Build comprehensive audit system with explainability.

### Rationale
- **Debugging** - Trace exact agent decisions
- **Compliance** - Audit trail for all actions
- **Performance** - Identify bottlenecks
- **Improvement** - Learn from agent interactions

### Implementation
- Audit service with multiple detail levels
- Explainability engine for decision analysis
- Performance metrics collection
- Statistical analysis endpoints

### Consequences
- Storage requirements for audit logs
- Performance impact (mitigated by levels)
- Privacy considerations for logged data

---

## ADR-009: Frontend Architecture

**Date:** 2024-01-12  
**Status:** Under Review

### Context
Need responsive UI for multi-agent chat.

### Decision
Single-page application with vanilla JavaScript.

### Rationale
- **Simplicity** - No build process required
- **Performance** - No framework overhead
- **Flexibility** - Direct DOM control
- **Learning Curve** - Easier for contributors

### Trade-offs
- More verbose than React/Vue
- Manual state management
- No component reusability

### Future Consideration
May migrate to React if complexity grows significantly.

---

## ADR-010: Task Orchestration

**Date:** 2024-01-18  
**Status:** Accepted

### Context
Need intelligent multi-agent coordination.

### Decision
Build orchestrator service with workflow templates.

### Rationale
- **Intelligence** - Route based on task understanding
- **Flexibility** - Support multiple workflow patterns
- **Efficiency** - Minimize agent handoffs
- **Visibility** - Track execution flow

### Implementation
- Orchestrator analyzes task with NLU
- Selects optimal workflow template
- Manages agent coordination
- Provides execution visibility

### Consequences
- Complex service to maintain
- Need to design good workflow templates
- Potential for routing mistakes (mitigated by confidence scores)

---

## Template for New ADRs

```markdown
## ADR-XXX: [Decision Title]

**Date:** YYYY-MM-DD  
**Status:** [Proposed|Accepted|Deprecated|Superseded]

### Context
[What is the issue that we're seeing that is motivating this decision?]

### Decision
[What is the change that we're proposing and/or doing?]

### Rationale
[Why is this the right decision?]

### Implementation
[How will this be implemented?]

### Consequences
[What becomes easier or more difficult because of this change?]
```