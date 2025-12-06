# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM Adventure is a text-based adventure game powered by LLMs with a sophisticated fact-based knowledge system. The game world operates on imperfect information where characters possess outdated or incorrect knowledge about a persistent, evolving world.

**Core Philosophy**: The game is heavily based on facts and interpretation of facts. History and change of facts are tracked closely. Characters possess imperfect, potentially outdated knowledge about the world. The system separates objective reality (Facts) from subjective belief (Knowledge).

## Architecture

### Backend API (Quart + PostgreSQL)

The backend is in the `api/` directory and uses:
- **Quart**: Async Python web framework (Flask-like API)
- **PostgreSQL + PostGIS**: Primary database with spatial extensions
- **LangChain**: LLM integration with streaming support
- **Pydantic**: Request/response validation

**Key Components**:
- `app.py`: Application factory with database initialization
- `run.py`: Entry point for running the server
- `routes/`: HTTP endpoints (general, world-building, errors)
- `agents/`: LLM agent implementations using LangChain LCEL
- `config/`: Database and LLM configuration
- `models/`: Pydantic models for request/response validation
- `utils/`: Logging utilities

### Database Architecture

The game uses a sophisticated triple-layer temporal tracking system:

**Layer 1 - World State (PostGIS)**:
- `locations`: Points of interest with WGS84 coordinates constrained to -40° to +40° (quarter-Earth planet)
- `location_history`: Immutable snapshots of location state over time
- `paths`: 3D routes between locations with elevation profiles (LINESTRING Z)
- `path_history`: Historical path states (blocked, destroyed, reopened)

**Layer 2 - Facts (Epistemic Layer)**:
- `facts`: Propositions about the world (can be TRUE or FALSE/cultural narratives)
- `fact_history`: Immutable fact snapshots preserving evolution
- `fact_relationships`: Many-to-many links between facts and entities with semantic roles

**Layer 3 - Character Knowledge**:
- `character_knowledge`: What characters believe with confidence levels, distortions, and personal context
- Supports supersession chains to track belief evolution (rumor → confirmation → correction)

### Spatial System

The world exists on a spherical planet (quarter-Earth size) using:
- **Coordinates**: WGS84 (SRID 4326) constrained to -40° to +40° range
- **Dual movement**: Graph-based (established paths) + coordinate-based (free wilderness movement)
- **PostGIS functions**: Handle all spatial calculations (distances, bearings, projections)
- **LLM integration**: Receives natural language context like "78km northeast, 4195m climb" not raw coordinates

### Temporal System

**Two time domains**:
- `TIMESTAMP`: Real-world database time (when records created)
- `BIGINT`: In-game time (can be paused, accelerated, rewound)

**Temporal integrity**:
- All mutable entities have history tables with `valid_from`/`valid_to` windows
- Facts reference specific LocationHistory snapshots
- CharacterKnowledge can reference historical fact versions
- Enables queries like "what did the world look like in year 1000?"

### LLM Integration

**Current setup**:
- Supports LM Studio (local) and Azure OpenAI
- Registry pattern in `config/llm.py` for easy LLM switching
- LangChain LCEL chains with structured output parsing
- World building data automatically persisted to PostgreSQL

**LLM receives processed context, not raw data**:
- PostGIS calculations → Natural language ("78km northeast")
- Fact queries → Filtered by character knowledge and belief strength
- Location descriptions → Rich narrative text fields

## Common Commands

### Initial Setup

```bash
# Create PostgreSQL database
psql -U postgres
CREATE DATABASE llm_adventure;
\q

# Install dependencies (choose one method)
cd api
uv sync                      # Recommended - fast!
# OR
pip install -r requirements.txt

# Configure environment
cd api
cp .env.example .env
# Edit .env with PostgreSQL credentials and LLM settings

# Run database migrations (REQUIRED before first run)
cd api
alembic upgrade head
```

### Running the Application

```bash
# API Server
cd api
python run.py
# Default: http://127.0.0.1:5000

# Or with custom host/port
HOST=0.0.0.0 PORT=8000 python run.py

# CLI Client (in separate terminal)
cd cli
python adventure_cli.py
```

### Testing World Building Endpoints

```bash
# Create world
curl -X POST http://127.0.0.1:5000/world-building/worlds \
  -H "Content-Type: application/json" \
  -d '{"name": "Test World", "description": "A test world"}'

# Describe world content  
curl -X POST http://127.0.0.1:5000/world-building/describe \
  -H "Content-Type: application/json" \
  -d '{"world_id": 1, "description": "A bustling market town..."}'
```

### Database Operations

```bash
# Connect to PostgreSQL
psql -U postgres -d llm_adventure

# Create a new migration after modifying SQLAlchemy models
cd api
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# Check current migration version
alembic current
```

## Development Patterns

### Adding New LLMs

Register in `config/llm.py`:
```python
def create_new_llm():
    return ChatOpenAI(...)

LLM_REGISTRY = {
    "lm_studio": create_lmstudio_qwen2_5_14b_instruct_llm,
    "azure_one": create_azure_one_gpt4o_llm,
    "new_llm": create_new_llm,  # Add here
}
```

Then use in routes:
```python
llm = current_app.llms.get('new_llm')
```

### Creating World Building Agents

Use LangChain LCEL pattern (see `agents/world_builder.py`):
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

chain = (
    WORLD_BUILDING_PROMPT
    | llm
    | parser
)
```

### Logging

Use structured logging via `utils/logging.py`:
```python
from utils.logging import get_logger

logger = get_logger(__name__)
logger.info("Message", key1=value1, key2=value2)
logger.error("Error occurred", error=e, context=ctx)
```

### Request Validation

Use Pydantic models (see `models/chat.py`):
```python
class MyRequest(BaseModel):
    field: str
    optional_field: Optional[int] = None

# In route
data = await request.get_json()
validated = MyRequest(**data)
```

### Database Queries

**For world-building data (SQLAlchemy ORM):**
```python
from config.orm_database import get_db_session
from db.models import World, Location, Fact

session = next(get_db_session())
worlds = session.query(World).all()
locations = session.query(Location).filter_by(world_id=1).all()
```

**For raw SQL queries:**
```python
from config.orm_database import get_engine

engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM worlds"))
```

**IMPORTANT**: Use SQLAlchemy models in `db/models.py` for database operations, not raw psycopg. The old `config/database.py` has been removed in favor of `config/orm_database.py`.

## Design Philosophy

### Fact Categories

**TRUE facts** (canonical_truth=TRUE):
- Categories: observed, historical, current_state, deduction, measurement
- What actually happened or exists in game world

**FALSE facts** (canonical_truth=FALSE):
- Categories: myth, legend, prophecy, conspiracy, religious, cultural, epic_tale
- Shared cultural narratives, not individual lies
- MUST have `created_by_character_id`
- Database constraints prevent accidental false facts

Individual character misunderstandings use `distortion_type` in CharacterKnowledge instead.

### Knowledge Divergence

Characters can have outdated knowledge:
1. Character learns fact linked to LocationHistory snapshot from year 1000
2. Location evolves, new LocationHistory created in year 1050
3. Character's knowledge still references old snapshot
4. LLM narrative: "You're surprised to find the village has grown into a bustling city"

### Semantic Roles

Facts connect to entities via `fact_relationships` with semantic roles:
- "Alice gave Bob a sword" → (character:Alice, role:giver), (character:Bob, role:receiver), (item:sword, role:gift)
- Enables rich queries: "Find all facts where Alice was a witness"

### Importance Scoring

Facts have dynamic importance based on:
- Number of character knowledge references
- Time since last referenced
- Facts below threshold (0.1) are candidates for cleanup
- Prevents database bloat while preserving history

## Project Structure

```
llm-adventure/
├── api/                      # Backend API server
│   ├── agents/              # LangChain agent implementations
│   ├── config/              # Database, LLM configuration
│   ├── db/                  # SQLAlchemy models and base
│   ├── migrations/          # Alembic database migrations
│   ├── models/              # Pydantic request/response models
│   ├── routes/              # HTTP endpoint blueprints
│   ├── services/            # Business logic layer
│   ├── utils/               # Logging utilities
│   ├── app.py               # Application factory
│   ├── run.py               # Server entry point
│   └── alembic.ini          # Alembic configuration
├── cli/                     # Interactive CLI client
│   ├── utils/               # Streaming utilities
│   ├── adventure_cli.py     # Main CLI entry point
│   ├── api_client.py        # HTTP client wrapper
│   ├── config.py            # CLI configuration
│   ├── display.py           # Rich console formatting
│   ├── models.py            # Pydantic models
│   └── state.py             # Session state management
├── gdd/                     # Game Design Documents
│   ├── Core Philosphy.md
│   ├── Database Schema Design - World Space.md
│   ├── Database Schema Design - Facts and Knowledge.md
│   └── Gameplay - New Game.md
└── CLAUDE.md                # This file
```

## Key Files to Understand

**Game Design & Philosophy:**
- `gdd/Core Philosphy.md`: Fact-based knowledge system, imperfect information, temporal tracking
- `gdd/Database Schema Design - World Space.md`: Spatial system, PostGIS integration, quarter-Earth planet
- `gdd/Database Schema Design - Facts and Knowledge.md`: Epistemic layer, character knowledge divergence

**World-Building System:**
- `CHECKLIST_SYSTEM.md`: Configurable requirements checklist for world creation
- `INTELLIGENT_WIZARD_EXAMPLE.md`: Vagueness detection and intelligent questioning
- `CHECKLIST_IMPLEMENTATION_COMPLETE.md`: Complete implementation summary

**Backend Core:**
- `api/app.py`: Quart application factory, startup hooks, blueprint registration
- `api/config/llm.py`: LLM registry pattern - add new LLMs here
- `api/config/orm_database.py`: SQLAlchemy session management (replaces old database.py)
- `api/db/models.py`: SQLAlchemy ORM models (World, Location, Fact)

**World Building System:**
- `api/agents/world_builder.py`: LangChain LCEL chain for natural language → structured data
- `api/services/world_building_service.py`: Business logic for world creation and LLM orchestration (includes wizard with checklist)
- `api/services/checklist_evaluator.py`: Evaluates gathered data against configurable requirements
- `api/config/world_requirements.py`: Configurable checklist - add/remove required fact types here
- `api/routes/world_building.py`: REST API endpoints
- `api/models/world_building.py`: Pydantic schemas for API contracts

**Database Migrations:**
- `api/migrations/env.py`: Alembic environment configuration
- `api/migrations/versions/`: Individual migration scripts (numbered sequentially)

**CLI Client:**
- `cli/adventure_cli.py`: Rich-based interactive menu system
- `cli/api_client.py`: Async HTTP client with error handling

## Important Implementation Notes

### Current MVP State
The current implementation is a **world-building MVP** with:
- ✅ Multi-world support
- ✅ Natural language extraction (locations + facts)
- ✅ Relative positioning (text-based, e.g., "north of Millbrook")
- ✅ SQLAlchemy ORM + Alembic migrations
- ✅ Service layer pattern
- ✅ **Multi-question adaptive wizard** with intelligent vagueness detection
- ✅ **Configurable checklist system** - developers can easily add/remove required fact types in `api/config/world_requirements.py`
- ✅ **Automatic quality control** - LLM checks checklist between each response and asks follow-up questions until requirements satisfied

**Not yet implemented** (see `api/IMPLEMENTATION_SUMMARY.md` for details):
- ❌ Temporal tracking (history tables, valid_from/valid_to)
- ❌ Character system and character knowledge
- ❌ Path/movement system
- ❌ Absolute PostGIS coordinates (constraint checking)
- ❌ Fact relationships with semantic roles
- ❌ FALSE facts (myths, legends, prophecies)

### Database Schema Management
- **Use Alembic migrations for all schema changes** - DO NOT modify tables directly
- Models are in `db/models.py` (SQLAlchemy) and `models/world_building.py` (Pydantic)
- The old `config/database.py` was removed; use `config/orm_database.py` instead
- Migrations are auto-generated: `alembic revision --autogenerate -m "message"`

### LLM Configuration
- LLMs are registered in `config/llm.py` using the registry pattern
- Supports both local (LM Studio) and cloud (Azure OpenAI) models
- Configuration via environment variables in `.env`
- Access in routes via `current_app.llms.get('llm_name')`

### Service Layer Pattern
The codebase follows strict separation of concerns:
```
Routes (HTTP) → Services (Business Logic) → Database (ORM/SQL)
```
- **Routes**: Handle HTTP requests, validation, responses only
- **Services**: Contain business logic, LLM orchestration, transaction management
- **Models**: SQLAlchemy for DB, Pydantic for API contracts

### CLI Architecture
- Rich console for beautiful terminal UI
- Async HTTP client with proper error handling
- State management tracks current world selection across menu navigation
- Modular design: config, display, api_client, models, state
