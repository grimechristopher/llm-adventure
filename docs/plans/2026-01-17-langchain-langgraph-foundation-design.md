# LangChain/LangGraph Foundation API Design

**Date**: 2026-01-17
**Status**: Approved
**Vision**: Stable, comprehensive foundation for building various types of LangChain/LangGraph applications

## Overview

A modular plugin-based framework using LangGraph as the universal orchestration layer. Supports conversational agents, autonomous agents, and data processing pipelines through a unified WebSocket API with PostgreSQL state persistence.

## Core Principles

1. **LangGraph-first**: All agents are LangGraph state graphs, regardless of type
2. **Modular plugins**: Self-contained agent modules with clear boundaries
3. **Streaming by default**: WebSocket-only API for consistent streaming experience
4. **Error recovery as first-class**: Framework provides patterns and utilities for graceful failure handling
5. **Simple > Complex**: Explicit registration, structured logging, fail-fast where appropriate

## Architecture

### High-Level Components

```
Client WebSocket → Core Server → Plugin Registry → Plugin Graph → Tools → Response Stream
```

**Core Framework** (`api/core/`):
- Plugin registry and lifecycle management
- Tool registry with hybrid (core + plugin) tools
- LLM factory with provider abstraction
- WebSocket server with connection management
- Error recovery utilities and decorators
- Structured logging setup
- PostgreSQL checkpointing wrapper

**Plugins** (`api/plugins/`):
- Self-contained modules (conversational, autonomous, data_pipeline)
- Each plugin defines LangGraph graphs, tools, state schemas
- Per-plugin LLM preferences
- Standard interface for registration

**Shared Infrastructure** (`api/shared/`):
- Core tools available to all plugins (web, database, files, LLM)
- Common Pydantic models
- Helper utilities

**Configuration** (`api/config/`):
- LLM providers and plugin preferences
- Database connection settings
- Application settings with environment validation

## Plugin Architecture

### Plugin Structure

```
api/plugins/conversational/
├── __init__.py              # Plugin class & registration
├── graphs/                  # LangGraph definitions
│   ├── chat.py
│   └── summarize.py
├── tools/                   # Plugin-specific tools
│   ├── chat_history.py
│   └── format_response.py
├── models.py                # Pydantic schemas for state/input/output
└── config.py                # Plugin settings (LLM preferences, etc.)
```

### Plugin Interface

```python
class Plugin:
    name: str                    # "conversational"
    graphs: Dict[str, StateGraph] # {"chat": chat_graph, "summarize": summarize_graph}
    tools: List[Tool]            # Plugin-specific tools
    llm_preference: str          # "gpt-4", "local-qwen", etc.

    def validate_input(self, graph_name: str, input: dict) -> bool
    def handle_error(self, error: Exception, context: dict) -> dict
```

### Plugin Registration

Explicit registration in `app.py` at startup:

```python
from plugins.conversational import ConversationalPlugin
from plugins.autonomous import AutonomousPlugin
from plugins.data_pipeline import DataPipelinePlugin

plugin_registry.register(ConversationalPlugin())
plugin_registry.register(AutonomousPlugin())
plugin_registry.register(DataPipelinePlugin())
```

### Plugin Lifecycle

1. Plugins registered at app startup
2. Each plugin's tools added to tool registry (namespaced)
3. LLM configured per plugin preference
4. Graphs compiled with checkpointer
5. Ready for execution via WebSocket requests

## WebSocket API Protocol

### Connection Flow

1. Client connects: `ws://localhost:5000/ws`
2. Client sends request with plugin/graph selection
3. Server streams events in real-time
4. Connection stays open for multiple requests

### Request Message Format

```json
{
  "request_id": "uuid",
  "plugin": "conversational",
  "graph": "chat",
  "input": {
    "message": "Hello, how are you?",
    "session_id": "user-123"
  },
  "config": {
    "llm_override": "gpt-4o",
    "checkpoint_id": "abc123"
  }
}
```

### Response Stream Events

```json
// Start event
{"type": "start", "request_id": "uuid", "timestamp": "..."}

// Node execution
{"type": "node", "node": "thinking", "state": {...}}

// Tool calls
{"type": "tool_call", "tool": "web_search", "args": {...}}
{"type": "tool_result", "tool": "web_search", "result": {...}}

// Token streaming (for LLM responses)
{"type": "token", "content": "Hello"}

// Final result
{"type": "result", "data": {...}, "checkpoint_id": "xyz789"}

// Errors
{"type": "error", "error": "...", "recoverable": true}
```

### Framework Responsibilities

- Connection management (reconnection, heartbeat)
- Request routing to plugins
- LangGraph streaming → WebSocket event mapping
- Checkpoint save/resume coordination
- Rate limiting per connection

## Tool Registry

### Hybrid Registry Design

```python
ToolRegistry:
  core_tools: List[Tool]               # Available to all plugins
  plugin_tools: Dict[str, List[Tool]]  # Namespaced by plugin

  def get_tools_for_plugin(plugin_name: str) -> List[Tool]:
      return core_tools + plugin_tools[plugin_name]
```

### Core Tools

Located in `api/shared/tools/`:

- **web.py**: `web_search`, `http_request`, `fetch_url`
- **database.py**: `query_database`, `execute_sql`
- **files.py**: `read_file`, `write_file`, `list_files`
- **llm.py**: `llm_call` (for sub-agents), `embed_text`

### Plugin Tools

Namespaced by plugin:

```python
# Conversational plugin
"conversational.get_chat_history"
"conversational.format_response"

# Autonomous plugin
"autonomous.plan_tasks"
"autonomous.validate_result"

# Data pipeline plugin
"data_pipeline.extract_structured"
"data_pipeline.validate_schema"
```

### Tool Definition Pattern

```python
from langchain.tools import tool

@tool
def web_search(query: str) -> str:
    """Search the web for information."""
    # Implementation
    return results
```

## LangGraph Patterns & Error Recovery

### Standard Graph Pattern

Every plugin follows a consistent graph structure:

```python
StateGraph:
  Nodes:
    - input_validation     # Validate/parse input
    - main_logic          # Core processing (LLM, tools, etc.)
    - error_recovery      # Handle recoverable errors
    - output_formatting   # Format final response

  Edges:
    input_validation → main_logic
    main_logic → output_formatting (on success)
    main_logic → error_recovery (on error)
    error_recovery → main_logic (retry) OR output_formatting (fallback)
```

### Error Recovery Utilities

Framework provides helpers in `api/core/error_recovery.py`:

```python
@error_boundary(recoverable=[ToolError, ValidationError])
def my_node(state):
    # If ToolError/ValidationError raised, routes to recovery node
    # Other errors fail fast
    pass

def create_retry_node(max_attempts=3, backoff=exponential):
    # Returns a pre-built retry node for common patterns
    pass

def create_fallback_node(fallback_value):
    # Returns a node that provides fallback when recovery fails
    pass
```

### Error Categories

1. **Recoverable** (route to recovery nodes):
   - Tool failures
   - Validation errors
   - LLM refusals
   - Rate limits

2. **Fail-fast** (bubble up immediately):
   - Database connection lost
   - Configuration errors
   - Programming bugs
   - Invalid plugin/graph names

### Example Graph with Recovery

```python
from core.error_recovery import create_retry_node, create_fallback_node

graph = StateGraph(ChatState)

graph.add_node("process", process_message)
graph.add_node("recover", create_retry_node(max_attempts=2))
graph.add_node("fallback", create_fallback_node("I couldn't process that."))

graph.add_edge("process", "output", condition=lambda s: not s.error)
graph.add_edge("process", "recover", condition=lambda s: s.error and is_recoverable(s.error))
graph.add_edge("recover", "process")  # Retry
graph.add_edge("recover", "fallback", condition=lambda s: s.attempts >= 2)
```

## State Management & Checkpointing

### State Schema Pattern

Each plugin defines state using TypedDict (LangGraph's preferred approach):

```python
# plugins/conversational/models.py
from typing import TypedDict, Optional, List

class ChatState(TypedDict):
    messages: List[Message]
    session_id: str
    user_context: dict
    error: Optional[Exception]
    attempts: int
    checkpoint_id: Optional[str]
```

### PostgreSQL Checkpointing

Using LangGraph's async PostgreSQL checkpointer:

```python
# Core framework setup (app.py)
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver(connection_string)
await checkpointer.setup()  # Creates checkpointing tables

# Plugin graphs get checkpointer
graph = StateGraph(ChatState)
# ... define nodes/edges ...
compiled_graph = graph.compile(checkpointer=checkpointer)
```

### Checkpoint Features

- **Auto-save**: State saved after each node execution
- **Resume**: Clients can resume from `checkpoint_id` in request
- **History**: Query past states for debugging/analytics
- **Time-travel**: Replay agent execution from any point

### Database Tables

Auto-created by LangGraph:

```sql
checkpoints         # State snapshots
checkpoint_writes   # Individual writes within checkpoint
checkpoint_metadata # Plugin name, graph name, timestamps
```

### Integration Strategy

- LangGraph checkpoints live in same PostgreSQL database
- Separate tables, no conflicts with application tables
- Can join on `session_id`/`user_id` for analytics
- Periodic cleanup of old checkpoints (configured via `MAX_CHECKPOINT_AGE_DAYS`)

### Best Practices

- Use SQLAlchemy's async engine with connection pooling
- Add indexes on `session_id` for query performance
- Plan for checkpoint cleanup strategy (age-based or count-based)
- Monitor checkpoint table sizes in production

## LLM Configuration

### LLM Factory

Central registry in `api/core/llm_factory.py`:

```python
class LLMFactory:
    providers: Dict[str, Callable]

    def register(self, name: str, factory: Callable):
        """Register an LLM provider"""

    def get(self, name: str, **kwargs) -> BaseChatModel:
        """Get configured LLM instance"""

    def get_for_plugin(self, plugin_name: str) -> BaseChatModel:
        """Get plugin's preferred LLM"""
```

### Provider Configuration

In `api/config/llm_config.py`:

```python
LLM_PROVIDERS = {
    "gpt-4": {
        "type": "azure_openai",
        "model": "gpt-4",
        "temperature": 0.7,
        "api_key": env.AZURE_API_KEY,
    },
    "gpt-4o": {
        "type": "azure_openai",
        "model": "gpt-4o",
        "temperature": 0.7,
    },
    "local-qwen": {
        "type": "lm_studio",
        "base_url": "http://localhost:1234/v1",
        "model": "qwen2.5-14b-instruct",
    },
}

PLUGIN_LLM_PREFERENCES = {
    "conversational": "gpt-4o",      # Fast, cheap for chat
    "autonomous": "gpt-4",            # Powerful for reasoning
    "data_pipeline": "local-qwen",    # Local for batch processing
}
```

### Plugin Usage

```python
class ConversationalPlugin:
    llm_preference = "gpt-4o"

    def build_graph(self, llm_factory: LLMFactory):
        llm = llm_factory.get(self.llm_preference)
        # Use llm in graph nodes
```

### Request-Level Override

Clients can override per-request:

```json
{
  "plugin": "conversational",
  "graph": "chat",
  "config": {"llm_override": "gpt-4"},
  "input": {...}
}
```

## Logging & Observability

### Logging Strategy

Simple structured logging using `structlog` (no LangSmith initially).

**Framework automatically logs**:
- WebSocket connections/disconnections
- Request routing (plugin/graph selection)
- Node execution (entry/exit, duration)
- Tool calls (name, args, results)
- Errors (with full context)
- Checkpoints (save/resume)

### Log Levels

- **DEBUG**: Node state transitions, tool args/results
- **INFO**: Request start/end, plugin routing, checkpoints
- **WARNING**: Recoverable errors, retries
- **ERROR**: Fail-fast errors, unhandled exceptions

### Structured Context Example

```python
logger.info(
    "node_executed",
    request_id=request_id,
    plugin="conversational",
    graph="chat",
    node="process_message",
    duration_ms=145,
    state_size=1024
)
```

### Log Storage & Output

**All logs stored as JSON** (`api/logs/app.log`):
```json
{"timestamp": "2026-01-17T10:32:15Z", "level": "info", "event": "node_executed", "request_id": "abc-123", "plugin": "conversational", "node": "process_message", "duration_ms": 145}
```

**Console output** (optional, for development):
```
2026-01-17 10:32:15 [INFO] node_executed
  request_id: abc-123
  plugin: conversational
  node: process_message
  duration_ms: 145
```

**Configuration**:
```python
# Development: JSON to file + pretty console
LOG_TO_CONSOLE = true

# Production: JSON to file only
LOG_TO_CONSOLE = false
```

### Plugin Logger

Framework provides logger to plugins:

```python
class Plugin:
    def __init__(self):
        self.logger = get_logger(f"plugin.{self.name}")
```

### Future Expansion

Easy to add LangSmith later since all events are already logged with structured context.

## Directory Structure

```
llm-adventure/
├── api/
│   ├── core/                          # Framework core
│   │   ├── __init__.py
│   │   ├── plugin_registry.py         # Plugin registration & discovery
│   │   ├── tool_registry.py           # Tool management
│   │   ├── llm_factory.py             # LLM provider factory
│   │   ├── websocket_server.py        # WebSocket handler
│   │   ├── error_recovery.py          # Error utilities & decorators
│   │   ├── logging.py                 # Structured logging setup
│   │   └── checkpoint_manager.py      # PostgreSQL checkpointing wrapper
│   │
│   ├── plugins/                       # Plugin modules
│   │   ├── __init__.py
│   │   ├── conversational/
│   │   │   ├── __init__.py            # Plugin class
│   │   │   ├── graphs/
│   │   │   │   ├── chat.py
│   │   │   │   └── summarize.py
│   │   │   ├── tools/
│   │   │   │   ├── chat_history.py
│   │   │   │   └── format_response.py
│   │   │   ├── models.py              # State schemas
│   │   │   └── config.py
│   │   ├── autonomous/
│   │   │   ├── __init__.py
│   │   │   ├── graphs/
│   │   │   │   ├── task_executor.py
│   │   │   │   └── planner.py
│   │   │   ├── tools/
│   │   │   │   ├── task_planner.py
│   │   │   │   └── validate_result.py
│   │   │   ├── models.py
│   │   │   └── config.py
│   │   └── data_pipeline/
│   │       ├── __init__.py
│   │       ├── graphs/
│   │       │   ├── extract.py
│   │       │   └── transform.py
│   │       ├── tools/
│   │       │   ├── extract_structured.py
│   │       │   └── validate_schema.py
│   │       ├── models.py
│   │       └── config.py
│   │
│   ├── shared/                        # Shared resources
│   │   ├── tools/                     # Core tools
│   │   │   ├── __init__.py
│   │   │   ├── web.py
│   │   │   ├── database.py
│   │   │   ├── files.py
│   │   │   └── llm.py
│   │   ├── models/                    # Shared Pydantic models
│   │   │   └── __init__.py
│   │   └── utils/                     # Helper functions
│   │       └── __init__.py
│   │
│   ├── config/                        # Configuration
│   │   ├── __init__.py
│   │   ├── llm_config.py              # LLM providers & preferences
│   │   ├── database.py                # PostgreSQL connection
│   │   └── settings.py                # App settings (.env loading)
│   │
│   ├── db/                            # Database
│   │   ├── models.py                  # SQLAlchemy models
│   │   └── base.py
│   │
│   ├── migrations/                    # Alembic migrations
│   │   └── versions/
│   │
│   ├── tests/                         # Tests
│   │   ├── core/                      # Framework tests
│   │   ├── plugins/                   # Plugin tests
│   │   └── integration/               # E2E tests
│   │
│   ├── logs/                          # Log files
│   │   └── app.log                    # JSON logs
│   │
│   ├── app.py                         # Application factory
│   ├── run.py                         # Server entry point
│   ├── requirements.txt
│   ├── .env.example
│   └── .env
│
├── cli/                               # Client
│   └── ...
│
├── docs/
│   └── plans/
│       └── 2026-01-17-langchain-langgraph-foundation-design.md
│
└── README.md
```

### Key Changes from Current Structure

- **Removed**: `routes/` (WebSocket-only, no REST routes)
- **Moved**: `agents/` → `plugins/*/graphs/`
- **Moved**: Business logic from `services/` into plugin graphs
- **Added**: `core/` for framework essentials
- **Added**: `plugins/` with standard structure for each agent type
- **Added**: `shared/` for common tools and utilities

## Security & Environment Configuration

### Environment Variables

`.env` file (never committed to git):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/llm_adventure
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# LLM Providers
AZURE_OPENAI_API_KEY=***
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-02-15-preview

OPENAI_API_KEY=***

LM_STUDIO_BASE_URL=http://localhost:1234/v1

# Application
SECRET_KEY=***  # For session signing, token generation
LOG_LEVEL=INFO
LOG_TO_CONSOLE=true
ENVIRONMENT=development  # development | production

# WebSocket
WS_MAX_CONNECTIONS=1000
WS_HEARTBEAT_INTERVAL=30
WS_MESSAGE_MAX_SIZE=1048576  # 1MB

# Security
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
RATE_LIMIT_PER_MINUTE=60
MAX_CHECKPOINT_AGE_DAYS=30  # Auto-cleanup old checkpoints
```

### Security Practices

**1. Never commit secrets**:

```gitignore
# .gitignore
.env
.env.local
.env.production
*.key
*.pem
```

**2. Environment validation**:

```python
# config/settings.py
from pydantic_settings import BaseSettings
from pydantic import SecretStr

class Settings(BaseSettings):
    database_url: str
    azure_openai_api_key: SecretStr
    secret_key: SecretStr

    class Config:
        env_file = ".env"

# Fails at startup if required vars missing
settings = Settings()
```

**3. WebSocket authentication** (optional, can add later):

```python
# In websocket_server.py
async def authenticate_connection(token: str):
    # Verify JWT/API key before allowing connection
    pass
```

**4. Input validation**:

```python
# All plugin inputs validated with Pydantic
from pydantic import BaseModel, Field
from uuid import UUID

class ChatInput(BaseModel):
    message: str = Field(max_length=10000)
    session_id: UUID
```

**5. SQL injection protection**:

- Use SQLAlchemy ORM (parameterized queries)
- Never string concatenate SQL
- All database queries go through ORM or parameterized raw SQL

**6. Rate limiting**:

```python
# Framework tracks requests per WebSocket connection
# Disconnect if exceeds RATE_LIMIT_PER_MINUTE
```

## Migration Path

Since this is a fresh start, here's the migration strategy:

### Phase 1: Core Framework
1. Build `core/` modules (plugin registry, tool registry, LLM factory, WebSocket server)
2. Setup PostgreSQL async checkpointing
3. Implement structured logging
4. Create error recovery utilities

### Phase 2: Plugin Infrastructure
1. Define plugin interface and base classes
2. Implement shared/core tools
3. Setup plugin discovery/registration

### Phase 3: First Plugin (Conversational)
1. Build conversational plugin as reference implementation
2. Implement chat graph with error recovery
3. Add chat history tool
4. Test end-to-end WebSocket flow

### Phase 4: Additional Plugins
1. Implement autonomous plugin (task execution, planning)
2. Implement data_pipeline plugin (extraction, transformation)
3. Test multi-plugin coordination

### Phase 5: Production Hardening
1. Add comprehensive tests (unit, integration, E2E)
2. Setup monitoring and alerting
3. Implement checkpoint cleanup jobs
4. Performance testing and optimization
5. Security audit

## Success Criteria

The foundation is successful when:

1. **Developers can easily add new plugins** without touching core code
2. **All agent types stream consistently** over WebSocket
3. **Errors are handled gracefully** with recovery or clear failure
4. **State persists reliably** with checkpointing
5. **Logs provide complete observability** for debugging
6. **Configuration is secure** with environment validation
7. **The codebase is straightforward** and well-organized

## Future Enhancements

Optional features to consider later:

- LangSmith integration for visual tracing
- WebSocket authentication/authorization
- Plugin hot-reloading (dynamic loading)
- Multi-agent coordination primitives
- Human-in-the-loop UI components
- Distributed deployment (multiple workers)
- Advanced checkpoint querying/analytics
- Plugin marketplace/discovery system

---

**End of Design Document**
