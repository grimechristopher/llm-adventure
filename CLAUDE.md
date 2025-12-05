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

# Install dependencies
cd api
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with PostgreSQL credentials
```

### Running the Application

```bash
# From api directory
python run.py

# Or with custom host/port via environment variables
HOST=0.0.0.0 PORT=8000 python run.py
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

# Enable PostGIS (if not already enabled)
CREATE EXTENSION IF NOT EXISTS postgis;

# Tables are auto-created on application startup
# See config/database.py:initialize_database()
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

Connection management via `config/database.py`:
```python
from config.database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT ...")
```

For world building data:
```python
from config.orm_database import get_db_session

session = next(get_db_session())
worlds = session.query(World).all()
```

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

## Key Files to Understand

- `gdd/Core Philosphy.md`: Core game design principles
- `gdd/Database Schema Design - World Space.md`: Detailed spatial schema design rationale
- `gdd/Database Schema Design - Facts and Knowledge.md`: Complete epistemic system design
- `api/app.py`: Application initialization and structure
- `api/agents/world_builder.py`: LangChain world-building extraction agent
- `api/config/database.py`: PostgreSQL connection management
- `api/config/llm.py`: LLM registry and factory functions

## Notes

- Database tables are created automatically on application startup
- World building data persists across sessions via PostgreSQL
- The system uses soft deletes (`deleted_at`) to preserve historical data
- PostGIS extension required for spatial queries
- In-game time (BIGINT) is separate from real-world time (TIMESTAMP)
- LangChain LCEL provides clean, composable agent pipelines
