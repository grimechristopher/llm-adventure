
# World Space

The game world exists on a **spherical planet approximately one quarter the size of Earth**. The world uses real-world geographic coordinate systems (WGS84) constrained to a smaller range, enabling natural spherical calculations while representing a smaller planet.

**World Dimensions**:
- Earth circumference: ~40,075 km
- Game world circumference: ~10,000 km (quarter size)
- Coordinate bounds: Longitude/Latitude from -40° to +40°
- Total playable area: ~8,900 km × ~8,900 km

The system uses **dual spatial representation**:
- **Coordinate-based**: For precise positioning, distance calculations, and free wilderness movement
- **Graph-based**: For established routes connecting locations via Paths

## Location

### Concept

Any point of interaction or interest is considered a **location**. Locations represent discrete places in the world where events occur, characters reside, and items exist. 

**Scale Flexibility**: Locations can contain other locations and vary dramatically in scale:
- A continent contains kingdoms
- A kingdom contains cities
- A city contains districts
- A district contains buildings
- A building contains rooms
- A room contains a specific chair

**Movement Model**: Locations are both:
- **Destinations**: Where characters arrive via paths or free travel
- **Origins**: Where journeys begin
- **Landmarks**: Points of reference for navigation and narrative

### Schema

```
locations
├── id                      INTEGER PRIMARY KEY
├── name                    VARCHAR(255) NOT NULL
├── coordinates             GEOGRAPHY(POINT, SRID 4326) NOT NULL
├── elevation_meters        INTEGER
├── location_type           VARCHAR(50) NOT NULL
├── description             TEXT
├── population              INTEGER
├── controlled_by_faction   VARCHAR(100)
├── boundary                GEOGRAPHY(POLYGON, SRID 4326)
├── parent_location_id      INTEGER FK → locations.id
├── created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
├── updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
└── deleted_at              TIMESTAMP

CONSTRAINTS:
- ST_X(coordinates) >= -40 AND ST_X(coordinates) <= 40
- ST_Y(coordinates) >= -40 AND ST_Y(coordinates) <= 40
- elevation_meters IS NULL OR (elevation_meters >= -500 AND elevation_meters <= 9000)

INDEXES:
- GiST index on coordinates (for spatial queries)
- GiST index on boundary (for area queries)
- Standard index on elevation_meters (for altitude filtering)
```

### Design Decisions

**coordinates (Geography POINT, SRID 4326)**

Uses PostgreSQL PostGIS Geography type with WGS84 standard (SRID 4326) constrained to -40° to +40° range:

- **Why WGS84?** Standard coordinate system supported by all mapping libraries and tools
- **Why constrained range?** Represents quarter-Earth planet while using proven spatial infrastructure
- **Spherical calculations**: Automatic longitude wrapping enables circumnavigation
- **Distance precision**: Calculations return meters along sphere surface
- **Efficient indexing**: GiST spatial indexes enable fast "nearby" queries
- **Direct export**: Converts to GeoJSON for D3.js visualization without transformation
- **LLM context**: PostGIS calculates distances; LLM receives "78km northeast" not raw coordinates

**elevation_meters (separate from coordinates)**

Stored as discrete integer column rather than 3D point geometry:

- **Query simplicity**: Easy to filter "locations above 3000m" for high-altitude content
- **LLM reasoning**: Clear numerical value for altitude comparisons
- **Nullable**: Can be NULL for locations where altitude is irrelevant (conceptual places, underwater)
- **Flexibility**: More practical than enforcing 3D geometry across entire system
- **Range validation**: -500m (underwater/underground) to 9000m (tallest peaks)

**location_type**

Categorical field for LLM context and query filtering:

- **Not rigidly constrained**: Allows organic evolution of location types
- **LLM context**: "Find all taverns within 10km" or "This is a mountain peak"
- **Examples**: port, city, village, tavern, mountain, forest, cave, shrine, ruin

**description (TEXT)**

**Critical for LLM narrative generation**:

- Contains sensory details, atmosphere, current condition
- This is what the LLM "sees" when generating responses
- Updated as locations evolve (bustling → ruined → rebuilt)
- Should be evocative: "A weathered stone tower rising from the mist, its upper floors long collapsed" vs "Tower"

**parent_location_id (hierarchical relationship)**

Enables nested location structure without artificial depth limits:

- **NULL parent**: Top-level geographic entities (continents, oceans, wilderness regions)
- **Hierarchical chains**: Continent → Kingdom → Province → City → District → Building → Room
- **Scale-agnostic**: A forest contains clearings; a clearing contains a specific ancient oak; the oak has a hollow (location)
- **Querying**: Recursive traversal enables "find all locations within Kingdom X"
- **Narrative context**: "You are in the throne room, in the palace, in the capital, in the Northern Kingdom"

**boundary (Geography POLYGON)**

Optional geographic extent for area-type locations:

- **When used**: Territories, city walls, forest extents, kingdoms, controlled zones
- **When NULL**: Point locations (a well, a tree, a statue)
- **Spatial queries**: "Is character within the city walls?"
- **Map visualization**: Render territory borders and controlled areas
- **Area mechanics**: Ownership, jurisdiction, magical zones

**population**

Tracks settlement size for cities, towns, villages:

- Can change over time (growth, decline, disasters)
- NULL for non-settlement locations
- Informs LLM: "bustling city of 50,000" vs "hamlet of 80 souls"

**controlled_by_faction**

Political/military control:

- Can change through conquest, treaty, rebellion
- NULL for unclaimed wilderness
- Enables factional queries: "all locations controlled by the Empire"

**deleted_at (soft delete)**

Locations can be destroyed but must remain in database:

- **Why soft delete?** Facts reference destroyed locations; character memories persist
- **Examples**: Burned villages, collapsed caves, sunken islands
- **Historical queries**: "What was here 50 years ago?"
- **Narrative**: "You stand in the ruins of what was once Millbrook"

### Location History

```
location_history
├── id                      INTEGER PRIMARY KEY
├── location_id             INTEGER FK → locations.id NOT NULL
├── name                    VARCHAR(255) NOT NULL
├── coordinates             GEOGRAPHY(POINT, SRID 4326) NOT NULL
├── elevation_meters        INTEGER
├── location_type           VARCHAR(50) NOT NULL
├── description             TEXT
├── population              INTEGER
├── controlled_by_faction   VARCHAR(100)
├── boundary                GEOGRAPHY(POLYGON, SRID 4326)
├── valid_from              BIGINT NOT NULL
├── valid_to                BIGINT
├── change_reason           TEXT
├── changed_by_event_id     INTEGER FK → events.id
└── created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP

CONSTRAINTS:
- valid_to IS NULL OR valid_to > valid_from
- Same coordinate and elevation constraints as Location

INDEXES:
- GiST index on coordinates (for historical spatial queries)
- GiST index on boundary
- Composite index on (location_id, valid_from, valid_to) for temporal queries
```

### History Design Rationale

**Purpose**: Immutable snapshots of location state at specific points in time.

**Temporal Validity Window**:
- `valid_from`: Unix timestamp when this state became current
- `valid_to`: Unix timestamp when this state ended (NULL = current state)
- Only one record per location has `valid_to = NULL` at any time

**Complete Field Duplication**:
- Every mutable field from Location table is copied to history
- Enables full reconstruction of world state at any historical moment
- "What did the entire world look like in year 1000?" → query all history records where `valid_from <= timestamp AND (valid_to > timestamp OR valid_to IS NULL)`

**Fact Integration**:
- Facts reference specific LocationHistory records via `location_history_id`
- When character learns about a place, their Fact links to the snapshot that existed at that moment
- Character knowledge persists even as reality changes
- Merchant knows "Millbrook is a village" (history record from 50 years ago)
- Traveler knows "New Millbrook is a city" (current history record)
- Both are valid knowledge states for different characters

**Change Tracking**:
- `change_reason`: Natural language explanation for LLM context ("Destroyed by dragon attack", "Grew due to trade boom")
- `changed_by_event_id`: Links to Event that caused the change, creating narrative causality chains

**Spatial Indexing on History**:
- Historical records retain GiST indexes
- Enables temporal-spatial queries: "What locations existed within 10km of this point in year 1000?"
- Reconstructing historical maps for character knowledge visualization

---

## Path

### Concept

Paths represent **traversable connections** between locations. Unlike simple graph edges, paths are physical routes with geographic extent, elevation profiles, and mutable properties.

**Path as Physical Route**: A path is not an abstraction—it's a real geographic line through the world:
- A dirt road winding through hills
- A river flowing between settlements
- A mountain pass with switchbacks
- A secret tunnel under the city
- A magical teleportation link

**Movement Model**:
- **Established routes**: Known, mapped paths characters can choose to follow (safer, faster, predictable)
- **Free movement alternative**: Characters can also ignore paths and travel through wilderness
- **Discovery**: New paths can be found; old paths can become lost or destroyed

### Schema

```
paths
├── id                      INTEGER PRIMARY KEY
├── name                    VARCHAR(255)
├── path_type               VARCHAR(50) NOT NULL
├── location_a_id           INTEGER FK → locations.id NOT NULL
├── location_b_id           INTEGER FK → locations.id NOT NULL
├── is_bidirectional        BOOLEAN DEFAULT TRUE
├── geometry                GEOGRAPHY(LINESTRINGZ, SRID 4326) NOT NULL
├── elevation_gain_meters   INTEGER
├── elevation_loss_meters   INTEGER
├── min_elevation           INTEGER
├── max_elevation           INTEGER
├── traversal_requirements  TEXT
├── danger_description      TEXT
├── description             TEXT
├── traversal_speed         DECIMAL(5,2) DEFAULT 1.0
├── is_visible              BOOLEAN DEFAULT TRUE
├── is_traversable          BOOLEAN DEFAULT TRUE
├── created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
└── updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP

CONSTRAINTS:
- location_a_id != location_b_id
- traversal_speed > 0
- path_type IN ('road', 'trail', 'river', 'trade_route', 'mountain_pass', 
                'sea_route', 'hidden_path', 'teleport', 'climbing_route', 'tunnel')

INDEXES:
- GiST index on geometry (for spatial queries)
- Standard index on location_a_id
- Standard index on location_b_id
- Composite index on (location_a_id, location_b_id)
```

### Design Decisions

**location_a_id / location_b_id (neutral naming)**

Named neutrally rather than "from/to" because paths are typically bidirectional:

- The geometry defines the physical route
- Either endpoint can be origin or destination
- `is_bidirectional` flag controls directional behavior
- Avoids confusion about which is "start" vs "end"

**is_bidirectional**

Explicitly stored flag for directional control:

- **TRUE (default)**: Can travel A→B or B→A
- **FALSE**: One-way only in geometry direction (A→B)
- **Examples of one-way paths**:
  - Waterfall descent (can go down, cannot climb up)
  - One-way teleportation gate
  - Drawbridge that only opens from inside castle
  - Secret door that only opens from one side
  - River with strong current

**geometry (LINESTRINGZ - 3D line)**

3D line with elevation at each vertex:

- **Format**: `LINESTRING Z(lon1 lat1 elev1, lon2 lat2 elev2, lon3 lat3 elev3, ...)`
- **Full elevation profile**: Not just endpoints—every point along route has altitude
- **Accurate distance**: Calculations account for terrain (uphill/downhill adds distance)
- **Sampling capability**: Can extract elevation at any point along path
- **Visual rendering**: 3D visualization shows route draped over terrain
- **Example**: `LINESTRING Z(-5.5 12.3 100, -5.2 12.5 800, -4.8 12.8 4200)` represents climb from 100m to 800m to 4200m

**elevation_gain_meters / elevation_loss_meters**

Pre-calculated from geometry for A→B direction:

- **Directional values**: Gain/loss values are for traveling A→B; reverse when going B→A
- **Why pre-calculate?** Performance—avoid recalculating on every query
- **Usage**:
  - Travel time estimation (climbing is slower)
  - Stamina/resource consumption
  - LLM narrative: "You face a grueling 2000m ascent"
  - Filtering: "Show me paths with less than 500m elevation gain"

**min_elevation / max_elevation**

Extracted from geometry's elevation range:

- **Enables queries**: "Find all paths that go above 3000m" for altitude-specific mechanics
- **LLM context**: High altitude affects difficulty, weather, visibility
- **Gameplay**: Thin air penalties, cold weather gear requirements, expanded sight range

**traversal_requirements (TEXT)**

Free-text LLM-readable description of prerequisites:

- **Not rigid categories**: Allows nuanced, evolving requirements
- **LLM reasoning**: Can evaluate if character meets requirements based on equipment/skills
- **Examples**:
  - "Requires climbing equipment for the final 300m ascent"
  - "Only passable on horseback; too narrow for wagons"
  - "Must be able to swim; underwater section spans 50 meters"
  - "Winter passage requires cold weather survival gear"
  - "Magical ward requires permission from the Council"

**danger_description (TEXT)**

Separate from requirements—path may be traversable but dangerous:

- **Requirements** = "Can I physically use this path?"
- **Dangers** = "What bad things might happen?"
- **Examples**:
  - "Frequent bandit ambushes in the narrow canyon"
  - "Avalanche risk in winter months above 3000m"
  - "Poisonous gas seeps from volcanic vents"
  - "Patrolled by enemy soldiers at night"
  - "Unstable ground; rockslides common"

**traversal_speed (DECIMAL)**

Movement speed multiplier relative to base:

- **1.0** = normal speed (baseline)
- **>1.0** = faster (paved roads, magical acceleration, downhill)
- **<1.0** = slower (steep terrain, dense jungle, muddy track)
- **Examples**: 
  - Paved highway: 1.5
  - Mountain trail: 0.4
  - Teleport: 999.0 (effectively instant)
- **Calculation**: Works with distance and elevation to determine travel time

**is_visible**

Can characters see/know about this path?

- **TRUE**: Common knowledge, appears on maps
- **FALSE**: Hidden routes requiring discovery or special knowledge
- **Examples**:
  - Smuggler routes through city sewers
  - Secret passages in castle walls
  - Forgotten ancient roads overgrown by forest
  - Magical doors only visible to certain races
- **Discovery mechanics**: Character might stumble upon hidden path, then it becomes visible to them

**is_traversable**

Can the path currently be used?

- **Dynamic flag**: Changes based on world events
- **TRUE**: Path is open
- **FALSE**: Path is blocked/destroyed
- **State changes**:
  - Bridge collapses in earthquake
  - Landslide blocks mountain pass
  - Winter snow closes high altitude routes (seasonal)
  - Magic seal prevents entry
  - Enemy army blocks the road
- **History tracking**: Old state preserved in PathHistory

**path_type**

Categorical descriptor for LLM context and mechanics:

- road, trail, river, trade_route, mountain_pass, sea_route, hidden_path, teleport, climbing_route, tunnel
- Informs how LLM describes travel
- Affects default speeds, dangers, requirements

### Path History

```
path_history
├── id                      INTEGER PRIMARY KEY
├── path_id                 INTEGER FK → paths.id NOT NULL
├── name                    VARCHAR(255)
├── path_type               VARCHAR(50) NOT NULL
├── location_a_id           INTEGER FK → locations.id NOT NULL
├── location_b_id           INTEGER FK → locations.id NOT NULL
├── is_bidirectional        BOOLEAN
├── geometry                GEOGRAPHY(LINESTRINGZ, SRID 4326) NOT NULL
├── elevation_gain_meters   INTEGER
├── elevation_loss_meters   INTEGER
├── min_elevation           INTEGER
├── max_elevation           INTEGER
├── traversal_requirements  TEXT
├── danger_description      TEXT
├── description             TEXT
├── traversal_speed         DECIMAL(5,2)
├── is_visible              BOOLEAN
├── is_traversable          BOOLEAN
├── valid_from              BIGINT NOT NULL
├── valid_to                BIGINT
├── change_reason           TEXT
├── changed_by_event_id     INTEGER FK → events.id
└── created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP

CONSTRAINTS:
- valid_to IS NULL OR valid_to > valid_from

INDEXES:
- GiST index on geometry
- Composite index on (path_id, valid_from, valid_to)
```

### History Design Rationale

Parallel to LocationHistory—immutable snapshots of path state over time.

**Critical Use Cases**:
- **Outdated directions**: Old merchant remembers "the mountain pass was safe and well-maintained" → references historical PathHistory when pass is now destroyed
- **Catastrophic changes**: Dragon destroys bridge → new PathHistory record with `is_traversable = FALSE`
- **Character knowledge**: NPCs give directions based on when they last traveled the route
- **Quest content**: "Restore the ancient trade route" requires knowing its historical configuration

**Geometry Evolution**:

The physical route itself can change, not just its properties:
- Erosion creates new switchbacks
- Engineers build shortcut tunnel (different line geometry)
- Earthquake shifts terrain, altering path alignment
- River changes course over decades
- Magical terraforming creates entirely new route

Each geometry change creates new history record, allowing Facts to reference the specific route configuration a character knew about.

---

## System Integration

### Coordinate System + Graph + Free Movement

The schema supports **three movement paradigms** working together:

**1. Path-Based Movement (Graph)**
- Character follows established Path from Location A to Location B
- Fast, predictable, safe(r)
- Known route, known destination
- Other travelers encountered
- Example: "I follow the mountain road to the next town"

**2. Free Movement (Coordinates)**
- Character travels in compass direction for specified distance
- Slower, unpredictable, higher risk
- LLM generates encounters, terrain, discoveries
- PostGIS calculates actual position: `ST_Project(current_coords, distance, bearing)`
- May discover new locations or create new paths
- Example: "I leave the road and head northeast through the forest for 10km"

**3. Spatial Awareness (Visualization + Context)**
- Coordinates determine what's visible from a location
- "You see smoke rising 20km to the east"
- "The mountain looms on the northern horizon"
- Character knowledge of places they've never visited
- Map rendering for players

### History + Facts + Character Knowledge

The history tables create the foundation for **imperfect information gameplay**:

**The Cycle**:
1. **State change**: Location or Path evolves (village grows into city, bridge collapses)
2. **History snapshot**: New LocationHistory or PathHistory record created with `valid_from` timestamp
3. **Fact creation**: Fact generated referencing the specific history record
4. **Character learning**: CharacterKnowledge links character to Fact
5. **World continues**: Current Location/Path continues to change
6. **Knowledge divergence**: Character's knowledge (linked to old history) becomes outdated relative to current reality

**Emergent Gameplay Examples**:
- NPC gives directions based on 20-year-old knowledge → player arrives to find everything changed
- Old map shows "village" → player finds thriving city
- Merchant remembers "safe mountain pass" → player discovers it's been destroyed
- Quest: Update royal maps by visiting locations and reporting current state
- Information becomes valuable: "Who has recent knowledge of the northern territories?"

### Soft Deletes vs. State Flags

**Locations use soft delete** (`deleted_at`):
- Destroyed places remain in database for historical reference
- Facts can still reference them
- "This was once a marketplace before the war"
- Enables restoration/rebuilding mechanics

**Paths use state flag** (`is_traversable`):
- Blocked paths aren't deleted, just marked impassable
- History tracks when/why they became blocked
- Can be repaired/reopened through gameplay
- Distinction between "temporarily blocked" and "destroyed"

### PostGIS → LLM Context Flow

**The LLM never works with raw coordinates**:

1. **Database stores**: `POINT(-5.5 12.3)` at 4200m elevation
2. **PostGIS calculates**: Distance = 78.4km, Bearing = 45° (northeast), Elevation change = +4195m
3. **Backend generates context**:
   ```
   From: Harbor Town (5m elevation)
   To: Dragon's Roost (4200m elevation)
   Distance: 78km northeast
   Climb: 4195m vertical ascent
   Route: 3 paths, 112km total, ~18 hours
   ```
4. **LLM receives natural language**, generates narrative response
5. **Player sees**: Map visualization + LLM-generated story

### PostGIS → D3.js Visualization Flow

**No coordinate transformation needed**:

1. **Database query**: Returns GeoJSON via `ST_AsGeoJSON(geometry)`
2. **API endpoint**: Serves standard GeoJSON FeatureCollection
3. **D3.js**: 
   - `d3.geoEquirectangular()` or `d3.geoMercator()` projection
   - `.fitExtent()` automatically scales to -40°/+40° bounds
   - `d3.geoPath()` renders points, lines, polygons
4. **Interactive map**: Click locations, highlight paths, show character position

**Both established paths AND free movement trails** render on same map using same coordinate system.

---

## Design Principles Summary

**1. Temporal Integrity**
- Every state change preserved in history
- Facts reference specific historical snapshots
- Characters can have outdated knowledge
- World evolution drives narrative

**2. Spatial Flexibility**
- Coordinates for visualization and free movement
- Graphs for established routes
- Both work together seamlessly
- PostGIS handles all spatial calculations

**3. LLM-Friendly**
- Natural language descriptions in TEXT fields
- Computed facts (distance, direction) provided as context
- Flexible categories, not rigid enums
- Rich narrative data in description fields

**4. Scalability**
- Hierarchical locations support any scale
- Soft deletes preserve history
- Indexed spatial queries remain fast
- Quarter-Earth size keeps world manageable

**5. Emergent Gameplay**
- Imperfect information creates discovery
- Knowledge becomes valuable commodity
- Character memories vs. current reality
- World changes based on events and time
