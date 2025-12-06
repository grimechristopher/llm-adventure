# Next Steps - Comprehensive World-Building System

## Current Status

✅ **Phase 1: Foundation - COMPLETE**

All core components implemented:
- Database schema with PostGIS, history tables, wizard sessions
- SQLAlchemy models with full relationships
- Coordinate mapper service with spatial intelligence
- Wizard orchestration with 2-stage flow
- API endpoints for wizard interaction

See `PHASE_1_IMPLEMENTATION.md` for complete details.

---

## Immediate Next Steps (Before Phase 2)

### 1. Database Setup

```bash
# Ensure PostgreSQL is running
sudo systemctl status postgresql

# Install PostGIS
sudo apt-get install postgresql-14-postgis-3

# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE llm_adventure;
CREATE USER your_username WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE llm_adventure TO your_username;

# Enable PostGIS (run in llm_adventure database)
\c llm_adventure
CREATE EXTENSION postgis;
```

### 2. Configure Environment

**File:** `api/.env`

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=llm_adventure
DB_USER=your_username
DB_PASSWORD=your_password

# LLM Configuration
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment

# OR for LM Studio
LM_STUDIO_BASE_URL=http://localhost:1234/v1
```

### 3. Run Migration

```bash
cd api
.venv/bin/alembic upgrade head
```

**Verify:**
```sql
-- Check tables created
\dt

-- Check PostGIS enabled
SELECT PostGIS_Version();

-- Check schema
\d locations
\d facts
\d world_generation_sessions
```

### 4. Test Wizard Flow

```bash
# Start API server
cd api
python run.py

# In another terminal - test wizard
cd api
python test_wizard.py  # Create this test script
```

**Test Script (api/test_wizard.py):**
```python
import asyncio
import httpx

async def test_wizard():
    async with httpx.AsyncClient() as client:
        # Create world
        resp = await client.post(
            "http://localhost:5000/world-building/worlds",
            json={"name": "Test World", "description": "A test world"}
        )
        world_id = resp.json()['id']
        print(f"Created world: {world_id}")

        # Start wizard
        resp = await client.post(
            "http://localhost:5000/world-building/wizard/start",
            json={"world_id": world_id}
        )
        session_id = resp.json()['session_id']
        print(f"Started session: {session_id}")
        print(f"Question: {resp.json()['first_question']}")

        # Answer world identity
        resp = await client.post(
            "http://localhost:5000/world-building/wizard/respond",
            json={
                "session_id": session_id,
                "response": "A high fantasy world with unstable ancient magic and floating sky islands"
            }
        )
        print(f"Next question: {resp.json()['next_question']}")

        # Answer locations
        resp = await client.post(
            "http://localhost:5000/world-building/wizard/respond",
            json={
                "session_id": session_id,
                "response": "Skyreach capital in the center. Far north is Frostpeak. South is Verdant Reach. Between Skyreach and Frostpeak is Ironhold."
            }
        )
        print(f"Complete: {resp.json()['is_complete']}")

        # Finalize
        resp = await client.post(
            "http://localhost:5000/world-building/wizard/finalize",
            json={"session_id": session_id}
        )
        print(f"Finalized: {resp.json()}")

if __name__ == "__main__":
    asyncio.run(test_wizard())
```

---

## Phase 2: Temporal System (Priority: Medium)

### Goal
Enable history tracking and temporal queries ("what did the world look like at year 1000?")

### Tasks

#### 1. Create HistorySnapshotService

**File:** `api/services/history_service.py` (NEW)

```python
class HistorySnapshotService:
    def create_location_snapshot(self, location: Location, valid_from: int, reason: str):
        """Create immutable snapshot of location state"""

    def create_fact_snapshot(self, fact: Fact, valid_from: int, reason: str):
        """Create immutable snapshot of fact state"""
```

#### 2. Add SQLAlchemy Event Listeners

**File:** `api/db/models.py` (UPDATE)

```python
from sqlalchemy import event

@event.listens_for(Location, 'before_update')
def receive_before_update(mapper, connection, target):
    """Create history snapshot before location update"""
    # Create LocationHistory record
```

#### 3. Create TemporalQueryService

**File:** `api/services/temporal_query_service.py` (NEW)

```python
class TemporalQueryService:
    def get_world_state_at_time(self, world_id: int, in_game_time: int):
        """Return locations and facts valid at specific time"""

    def get_location_history(self, location_id: int):
        """Return all historical versions of a location"""

    def get_fact_evolution(self, fact_id: int):
        """Return fact supersession chain"""
```

#### 4. Add API Endpoints

**File:** `api/routes/world_building.py` (UPDATE)

```python
@world_building_routes.route('/worlds/<int:world_id>/state', methods=['GET'])
async def get_world_state():
    """Query historical state: ?at_time=1000"""

@world_building_routes.route('/locations/<int:location_id>/history', methods=['GET'])
async def get_location_history(location_id: int):
    """Get location evolution timeline"""
```

**Estimated Time:** 1-2 days

---

## Phase 3: FALSE Facts Support (Priority: Medium)

### Goal
Enable myths, legends, and cultural narratives as first-class entities

### Tasks

#### 1. Create MythExtractionAgent

**File:** `api/agents/myth_builder.py` (NEW)

```python
MYTH_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Extract myths, legends, and cultural beliefs...

    Categories:
    - myth: Origin stories, cosmology
    - legend: Heroic tales, embellished history
    - prophecy: Predictions about the future
    - religious: Faith-based beliefs
    - cultural: Societal traditions
    """),
    ("user", "{description}")
])

def create_myth_extraction_chain(llm):
    """Create chain for extracting FALSE facts"""
```

#### 2. Update Wizard with Culture Stage

**File:** `api/services/world_building_service.py` (UPDATE)

```python
class WizardOrchestrationService:
    STAGES = ['world_identity', 'locations', 'culture', 'complete']

    STAGE_QUESTIONS = {
        'culture': "What legends, myths, or cultural beliefs exist in your world?"
    }
```

#### 3. Add Myth Query Endpoint

**File:** `api/routes/world_building.py` (UPDATE)

```python
@world_building_routes.route('/worlds/<int:world_id>/myths', methods=['GET'])
async def get_myths(world_id: int):
    """List all FALSE facts (myths, legends, prophecies)"""
    facts = db.query(Fact).filter(
        Fact.world_id == world_id,
        Fact.canonical_truth == False
    ).all()
```

**Estimated Time:** 1 day

---

## Phase 4: Advanced Wizard (Priority: Low)

### Goal
Make wizard fully adaptive with LLM-driven question selection

### Tasks

#### 1. Create Question Registry

**Directory:** `api/services/wizard_questions/` (NEW)

```python
# base.py
class QuestionType(ABC):
    name: str
    prompt_template: str
    extraction_schema: Type[BaseModel]
    completion_criteria: Callable

# world_identity.py
class WorldIdentityQuestion(QuestionType):
    name = "world_identity"
    # ...

# QUESTION_REGISTRY
QUESTION_REGISTRY = {
    "world_identity": WorldIdentityQuestion(),
    "locations": LocationsQuestion(),
    "magic_system": MagicSystemQuestion(),
    "technology": TechnologyLevelQuestion(),
    "culture": CultureQuestion(),
}
```

#### 2. Implement LLM Completion Logic

**File:** `api/services/world_building_service.py` (UPDATE)

```python
async def _is_stage_complete(self, session):
    """Use LLM to evaluate completion"""
    evaluation = await self.completion_chain.ainvoke({
        "gathered_data": session.gathered_data
    })
    return evaluation.is_complete
```

#### 3. Add Progress Tracking to CLI

**File:** `cli/adventure_cli.py` (UPDATE)

```python
# Show progress bar
progress = response['progress_percentage']
console.print(f"[green]Progress: {progress}%[/green]")
```

**Estimated Time:** 2-3 days

---

## Phase 5: Spatial Intelligence Polish (Priority: Low)

### Goal
Handle complex coordinate mapping edge cases

### Tasks

#### 1. Enhanced Coordinate Logic

**File:** `api/services/coordinate_mapper.py` (UPDATE)

```python
def _calculate_midpoint(self, loc1, loc2):
    """Handle 'between X and Y' patterns"""

def _handle_multiple_constraints(self, constraints):
    """Handle 'east of mountains, near coast'"""
```

#### 2. GeoJSON Export

**File:** `api/routes/world_building.py` (UPDATE)

```python
@world_building_routes.route('/worlds/<int:world_id>/geojson', methods=['GET'])
async def export_geojson(world_id: int):
    """Export locations as GeoJSON for D3.js visualization"""
```

#### 3. PostGIS Utilities

**File:** `api/utils/postgis_utils.py` (NEW)

```python
def project_coordinate(lat, lon, distance_m, bearing):
    """Wrapper for ST_Project"""

def calculate_distance(loc1, loc2):
    """Wrapper for ST_Distance"""

def natural_language_distance(distance_km):
    """150km → '3 days travel by foot'"""
```

**Estimated Time:** 1-2 days

---

## Phase 6: Migration & Polish (Priority: Medium)

### Goal
Production-ready system with clean migration path

### Tasks

#### 1. Migration Script

**File:** `api/scripts/migrate_existing_worlds.py` (NEW)

```python
def migrate_existing_worlds():
    """
    - Create wizard sessions for existing worlds (mark complete)
    - Assign coordinates to existing locations
    - Create initial history snapshots
    """
```

#### 2. Backward Compatibility

**File:** `api/routes/world_building.py` (UPDATE)

```python
@world_building_routes.route('/describe', methods=['POST'])
async def describe_world():
    """Single-shot extraction (backward compatible)

    Optionally uses wizard under the hood if ?use_wizard=true
    """
```

#### 3. Performance Optimization

```sql
-- Add composite indexes
CREATE INDEX idx_loc_world_created ON locations(world_id, created_at);
CREATE INDEX idx_loc_hist_temporal ON location_history(location_id, valid_from, valid_to);
CREATE INDEX idx_wg_sessions_stage ON world_generation_sessions(session_stage);
```

#### 4. Documentation Updates

- Update `CLAUDE.md` with wizard flow
- Update `SETUP.md` with PostGIS installation
- Create API documentation (OpenAPI/Swagger)

**Estimated Time:** 2 days

---

## Total Timeline Estimate

- **Phase 2** (Temporal): 1-2 days
- **Phase 3** (FALSE Facts): 1 day
- **Phase 4** (Advanced Wizard): 2-3 days
- **Phase 5** (Spatial Polish): 1-2 days
- **Phase 6** (Migration & Polish): 2 days

**Total:** 7-10 days for complete system

---

## Testing Strategy

### Unit Tests (Recommended)
```bash
pytest api/tests/test_coordinate_mapper.py
pytest api/tests/test_wizard_service.py
pytest api/tests/test_temporal_queries.py
```

### Integration Tests
```bash
pytest api/tests/test_wizard_integration.py
```

### End-to-End Tests
```bash
# Test full wizard flow via CLI
cd cli
python test_e2e_wizard.py
```

---

## Current Decision Points

**Question 1:** Should we proceed with Phase 2 (Temporal) or Phase 3 (Myths) first?
- **Temporal**: More architectural, enables time-based gameplay
- **Myths**: More feature-rich, enables cultural depth

**Question 2:** Do you want to test Phase 1 first or continue implementation?
- **Test First**: Validate foundation before building on it
- **Continue**: Trust the architecture, iterate later

**Question 3:** Should we add automated tests as we go or after completion?
- **As We Go**: Slower but safer
- **After**: Faster iteration, refactor with tests later

---

## Success Metrics

### Phase 1 (Current)
- ✅ Migration runs successfully
- ✅ Wizard creates world with coordinates
- ✅ PostGIS queries work correctly
- ✅ JSONB session data persists

### Phase 2 (Temporal)
- Location updates create history snapshots
- Can query "world at year 1000"
- Fact evolution chains work

### Phase 3 (Myths)
- Wizard extracts myths as FALSE facts
- Database constraints prevent invalid myths
- Can query myths separately from TRUE facts

### Complete System
- All 6 phases implemented
- Existing worlds migrate cleanly
- Performance meets targets (<2s wizard response)
- GeoJSON export works for D3.js

---

## Resources

**Documentation:**
- PostGIS: https://postgis.net/documentation/
- LangChain LCEL: https://python.langchain.com/docs/expression_language/
- GeoAlchemy2: https://geoalchemy-2.readthedocs.io/

**Tools:**
- PostGIS Viewer: QGIS (https://qgis.org/)
- API Testing: Postman, HTTPie, or curl
- Database: pgAdmin, DBeaver

**Next File to Create:**
- `api/test_wizard.py` - Basic wizard test script
- `api/.env.example` - Example environment configuration
