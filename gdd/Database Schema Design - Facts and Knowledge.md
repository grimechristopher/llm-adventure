# Facts and Knowledge System

The game maintains a **dual-layer epistemic engine** that separates objective reality from subjective belief. This architecture enables emergent storytelling through imperfect information, misinformation, evolving understanding, and cultural narratives that exist independent of truth.

**Core Concept**: Characters don't perceive reality—they perceive facts. And facts can be true, false, outdated, distorted, or forgotten. The system tracks both what IS (objective facts) and what characters BELIEVE (subjective knowledge).

**Time System**:
- **TIMESTAMP**: Real-world database time (when records created/modified)
- **BIGINT**: In-game time (can be paused, accelerated, or rewound; independent of real time)

The system uses **triple-layer temporal tracking**:
- **Fact evolution**: How objective reality changes over time
- **Knowledge evolution**: How individual understanding changes over time
- **Location history integration**: Facts reference historical snapshots of places

---

## Fact

### Concept

A **fact** is a proposition about the world—an informational object that exists independent of whether any character knows it. Facts are the building blocks of both truth and fiction in the game world.

**Two Fundamental Categories**:

**Canonical Truth (TRUE)**: Objective reality that actually happened or exists
- "The northern bridge collapsed on Winterday 15, Year 1247"
- "Dragon's Roost peak reaches 4,200 meters elevation"
- "Guild assassin Varek murdered merchant Aldric in the marketplace"

**Cultural Narrative (FALSE)**: Myths, legends, prophecies, conspiracies
- "The Dragon God sleeps beneath the mountain"
- "The northern lights are spirits of ancient warriors"
- "The Duke died of natural causes" (coordinated cover-up)

**Why Allow False Facts?**

False facts are not individual errors—they are **shared cultural objects**:
- Myths and legends that entire regions believe
- Religious doctrines that shape societies
- Conspiracies coordinated by multiple actors
- Prophecies that may later be fulfilled
- Epic tales that evolve through retelling

False facts enable queries like "what legends exist about this location?" and support cultural identity through shared beliefs.

**Entity Relationships**: Facts are connected to game entities (characters, locations, items, events) through a many-to-many `FactRelationship` table with **semantic roles**:
- "Alice gave Bob a sword" → relationships: (character, Alice, 'giver'), (character, Bob, 'receiver'), (item, sword, 'gift')
- "Army marched from CityA to CityB" → relationships: (location, CityA, 'origin'), (location, CityB, 'destination')

### Schema

```
facts
├── id                          INTEGER PRIMARY KEY
├── content                     VARCHAR(2000) NOT NULL
├── fact_category               VARCHAR(30) NOT NULL
├── canonical_truth             BOOLEAN DEFAULT TRUE
├── what_type                   VARCHAR(50)
├── when_occurred               BIGINT
├── why_context                 TEXT
├── where_location_history_id   INTEGER FK → location_history.id
├── importance_score            DECIMAL(3,2) DEFAULT 0.5
├── last_referenced             BIGINT
├── superseded_by_fact_id       INTEGER FK → facts.id
├── superseded_at               BIGINT
├── created_by_character_id     INTEGER FK → characters.id
├── created_by_event_id         INTEGER FK → events.id
└── generated_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP

CONSTRAINTS:
- LENGTH(content) BETWEEN 1 AND 2000
- importance_score BETWEEN 0.0 AND 1.0
- (canonical_truth = TRUE AND fact_category IN ('observed', 'historical', 'current_state', 'deduction', 'measurement')) OR
  (canonical_truth = FALSE AND fact_category IN ('myth', 'legend', 'prophecy', 'conspiracy', 'religious', 'cultural', 'epic_tale'))
- (fact_category IN ('myth', 'legend', 'prophecy', 'religious', 'cultural', 'epic_tale') REQUIRES created_by_character_id NOT NULL)
- (superseded_by_fact_id NOT NULL) REQUIRES (superseded_at NOT NULL)

INDEXES:
- Standard index on when_occurred (temporal queries)
- Standard index on fact_category (category filtering)
- Standard index on importance_score (cleanup queries)
- Standard index on last_referenced (staleness detection)
- Partial index on id WHERE canonical_truth = TRUE (truth queries)
```

### Design Decisions

**content (VARCHAR 2000)**

The human-readable proposition that LLM and players see:

- **Length limit**: Prevents LLM bloat while allowing detailed descriptions
- **Active voice**: "The bridge collapsed" not "Bridge collapse occurred"
- **Specificity**: "The northern bridge over Serpent River collapsed" not "A bridge collapsed"
- **LLM integration**: This is what LLM "reads" when generating dialogue/narrative
- **Contextual details**: Important information embedded naturally for fluid generation

**Why 2000 characters?** 
- Sufficient for detailed facts: "During the winter solstice ceremony, High Priestess Elara performed the ritual of renewal at the Temple of Dawn, witnessed by over 500 citizens including the Duke and his retinue..."
- Prevents abuse: Stops facts from becoming multi-paragraph essays
- Query performance: Shorter strings mean faster indexes and searches

**fact_category (constrained by canonical_truth)**

Critical constraint preventing casual creation of false facts:

**TRUE categories** (what actually happened):
- `observed`: Witnessed firsthand by characters
- `historical`: Past events confirmed through evidence
- `current_state`: Current conditions (population, weather, control)
- `deduction`: Logical conclusions from evidence
- `measurement`: Quantitative facts (distances, elevations, temperatures)

**FALSE categories** (cultural narratives):
- `myth`: Origin stories, cosmology, supernatural explanations
- `legend`: Heroic tales, possibly based on truth but embellished
- `prophecy`: Predictions about the future
- `conspiracy`: Coordinated lies created by specific characters
- `religious`: Faith-based beliefs about deities, afterlife, morality
- `cultural`: Societal beliefs about traditions, taboos, customs
- `epic_tale`: Grand narratives of historical events (exaggerated)

**Why constraint?**
- **Prevents accidents**: Can't mark facts false without explicit category
- **Forces intentionality**: Creating myths requires conscious decision
- **Query clarity**: "Find all myths in region X" vs "find all lies"
- **LLM context**: Category tells LLM how to treat the information

**canonical_truth (BOOLEAN)**

TRUE: Objectively happened/exists in game world
FALSE: Cultural narrative, myth, legend, or conspiracy

**Critical nuance**: FALSE doesn't mean "individual character's lie." Individual deceptions are handled through `distortion_type` in CharacterKnowledge. FALSE means "shared cultural objects that exist as legitimate beliefs independent of any individual."

**Examples**:
- Merchant lies about prices → TRUE fact about actual price + merchant has distorted knowledge
- Entire culture believes Dragon God → FALSE fact as shared cultural object

**what_type (categorical descriptor)**

Broad classification for filtering and LLM context:

- **Examples**: movement, crime, discovery, political_change, natural_disaster, combat, trade, birth, death, revelation
- **Not rigidly constrained**: Allows organic evolution of types
- **Query support**: "All crime-related facts at this location in past month"
- **LLM reasoning**: Helps LLM understand context and generate appropriate responses

**when_occurred (BIGINT in-game time)**

When the fact became true (or when cultural narrative was established):

- **For TRUE facts**: When the event actually happened in game world
- **For FALSE facts**: When the myth/legend/prophecy was first created
- **NULL**: Timeless facts ("The mountain is 4200m tall")
- **Temporal queries**: Enable "what facts occurred between Year 1000 and 1100?"
- **Knowledge divergence**: Character learns fact at one time, world changes later

**why_context (TEXT)**

Narrative explanation of circumstances:

- **Causality**: "The bridge collapsed due to flooding from unprecedented rainfall"
- **Origin story**: "The myth arose after series of earthquakes shook the region"
- **Cover story**: "This conspiracy was created to hide the assassination from public"
- **LLM context**: Helps LLM explain why events happened and generate coherent story

**where_location_history_id (historical snapshot reference)**

Links to **specific LocationHistory snapshot** that existed when fact was created:

**This is critical for knowledge divergence**:
- Character learns "Millbrook is a village" in Year 1000 → fact references LocationHistory from Year 1000
- Millbrook grows into city in Year 1050 → new LocationHistory created
- Character's knowledge still points to old snapshot
- Current reality reflects new snapshot
- Both are valid in their temporal contexts

**Different from where_location_id**: We removed direct location reference in favor of always using historical snapshots for temporal integrity.

**importance_score (DECIMAL 0.0-1.0)**

Dynamic metric for fact relevance:

- **Calculated, not manual**: Based on knowledge references and recency
- **Formula**: `min(1.0, (knowledge_count * 0.1) * time_decay)`
- **Time decay**: Unreferenced facts lose importance over 30 days
- **Cleanup trigger**: Facts below threshold (0.1) are candidates for deletion
- **Priority display**: High-importance facts shown first in UI
- **LLM context pruning**: Include only facts above threshold to manage token limits

**last_referenced (BIGINT in-game time)**

Most recent time this fact was:
- Added to character knowledge
- Mentioned in dialogue
- Used in LLM context generation
- Queried by system

**Staleness detection**: Facts unreferenced for long periods become candidates for cleanup, preventing database bloat.

**superseded_by_fact_id (self-reference)**

Links to the fact that replaces this one:

**Use cases**:
- Location evolution: "Millbrook is a village" → "Millbrook is a city"
- Status changes: "The pass is safe" → "The pass is blocked by avalanche"
- Prophecy fulfillment: FALSE prophecy → TRUE historical fact when fulfilled
- Information correction: "Duke died naturally" → "Duke was assassinated"

**Chain traversal**: Can walk supersession chain to see how truth evolved over time

**Different from knowledge chains**: This tracks objective reality evolution, not individual belief evolution

**superseded_at (BIGINT in-game time)**

When this fact was superseded:

- **Required if superseded**: Database enforces timestamp when superseded_by_fact_id is set
- **Temporal queries**: "What was the state of facts at Year 1050?"
- **History reconstruction**: Enables time-travel queries through fact evolution

**created_by_character_id (Character FK)**

**REQUIRED for FALSE facts**: Who invented this myth/legend/conspiracy?

- **Authorship tracking**: Bard who composed the epic tale
- **Source identification**: Priest who established religious doctrine
- **Conspiracy tracking**: Who fabricated the cover story
- **NULL for TRUE facts**: Observed reality isn't "created" by anyone
- **Database enforced**: Constraint ensures all false facts have creators
- **Query support**: "All myths created by this character"

**created_by_event_id (Event FK)**

Optional link to event that generated this fact:

- **Causal chains**: Combat event → "Character defeated enemy" fact
- **Information flow**: Dialogue event → "Secret passage revealed" fact
- **Natural consequences**: Earthquake event → "Temple destroyed" fact
- **Narrative tracking**: Walk event chains to understand story causality

**generated_at (TIMESTAMP real-world time)**

When this record was added to database:

- **Different from when_occurred**: Real-world time vs in-game time
- **Debugging**: Track when facts were created in actual chronological order
- **Audit trail**: Understand database growth patterns
- **Performance analysis**: Identify fact creation bottlenecks

### Fact History

```
fact_history
├── id                          INTEGER PRIMARY KEY
├── fact_id                     INTEGER FK → facts.id NOT NULL
├── content                     VARCHAR(2000) NOT NULL
├── fact_category               VARCHAR(30) NOT NULL
├── canonical_truth             BOOLEAN NOT NULL
├── what_type                   VARCHAR(50)
├── when_occurred               BIGINT
├── why_context                 TEXT
├── where_location_history_id   INTEGER FK → location_history.id
├── importance_score            DECIMAL(3,2)
├── valid_from                  BIGINT NOT NULL
├── valid_to                    BIGINT
├── change_reason               TEXT
├── changed_by_event_id         INTEGER FK → events.id
└── created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP

CONSTRAINTS:
- valid_to IS NULL OR valid_to > valid_from
- LENGTH(content) BETWEEN 1 AND 2000

INDEXES:
- Composite index on (fact_id, valid_from, valid_to) for temporal queries
- Partial index on (fact_id) WHERE valid_to IS NULL (current snapshots)
```

### History Design Rationale

**Purpose**: Immutable snapshots of fact state at specific points in time.

**When facts change**:

**Content evolution**: Myth gets retold with variations
- Original (Year 500): "The First King received his crown from the gods"
- Updated (Year 800): "The First King received his crown from the gods after slaying the demon lord"
- History preserves both versions with temporal validity windows

**Truth status changes**: Prophecy fulfilled
- Year 1000: FALSE prophecy "The red comet signals the king's death"
- Year 1050: King dies during red comet
- Updated to TRUE historical fact, prophecy version preserved in history

**Category reclassification**: Myth confirmed as historical
- FALSE 'myth': "Ancient civilization built the ruins"
- Archaeological discovery proves it true
- Becomes TRUE 'historical' fact, myth version preserved

**Temporal Validity Window**:
- `valid_from`: In-game timestamp when this version became current
- `valid_to`: In-game timestamp when superseded (NULL = still current)
- Only one record per fact has `valid_to = NULL` at any time

**CharacterKnowledge Integration**:

CharacterKnowledge can reference **either**:
- Current Fact (most common)
- Specific FactHistory snapshot (for outdated knowledge)

**Example Knowledge Divergence**:
```
Year 1000: Fact created "The pass is safe"
  → FactHistory #1 (valid_from=1000, valid_to=NULL)

Year 1025: Character learns about pass
  → CharacterKnowledge references FactHistory #1

Year 1050: Avalanche blocks pass, fact updated "The pass is blocked"
  → FactHistory #1 (valid_to=1050, superseded)
  → FactHistory #2 (valid_from=1050, valid_to=NULL, current)

Year 1075: Character's knowledge still references FactHistory #1
  → They believe "pass is safe" (outdated)
  → Current reality is "pass blocked" (FactHistory #2)
```

**change_reason (TEXT)**

Natural language explanation for LLM context:
- "Myth evolved through oral retelling by traveling bards"
- "Prophecy fulfilled when king died during red comet appearance"
- "Archaeological evidence confirmed historical accuracy of legend"
- "Conspiracy exposed by investigative character discovering documents"

**Narrative continuity**: LLM can explain why character's outdated knowledge diverges from current reality, creating organic storytelling moments.

---

## Fact Relationship

### Concept

Facts connect to game entities (characters, locations, items, events) through **many-to-many relationships with semantic roles**. This solves the problem of facts involving multiple entities in different capacities.

**The Problem**: A fact like "Alice gave Bob a sword in the tavern" involves:
- Two characters (one giving, one receiving)
- One item (being given)
- One location (where it happened)

Old approaches using single foreign keys (who_id, where_id) couldn't represent this complexity. The solution: **semantic role-based relationships**.

**Role Examples**:
- **subject**: Primary actor in the fact
- **victim**: Character harmed or affected negatively
- **witness**: Character who observed the event
- **giver/receiver**: Transfer of items
- **origin/destination**: Movement between locations
- **tool**: Item used to accomplish action
- **combatant**: Participant in combat
- **scene**: Location where event occurred

### Schema

```
fact_relationships
├── fact_id                 INTEGER FK → facts.id PRIMARY KEY
├── related_entity_type     VARCHAR(20) NOT NULL PRIMARY KEY
├── related_entity_id       INTEGER NOT NULL PRIMARY KEY
├── role                    VARCHAR(30)
├── is_primary              BOOLEAN DEFAULT FALSE
├── relationship_strength   DECIMAL(3,2) DEFAULT 1.0
├── created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
└── deleted_at              TIMESTAMP

CONSTRAINTS:
- related_entity_type IN ('character', 'location', 'item', 'event')
- relationship_strength BETWEEN 0.0 AND 1.0

INDEXES:
- Composite index on (related_entity_type, related_entity_id) for "find facts about entity"
- Partial index on (fact_id, is_primary) WHERE is_primary = TRUE
- Composite index on (related_entity_type, role) for role-based queries
- Composite index on (fact_id, related_entity_type) for fact-centric queries
```

### Design Decisions

**related_entity_type (VARCHAR 20)**

Type of entity this fact relates to:

- **character**: NPCs, players, creatures
- **location**: Places, regions, buildings
- **item**: Objects, weapons, containers
- **event**: Other events referenced by this fact

**Polymorphic foreign key**: The combination of (entity_type, entity_id) identifies any game entity.

**role (VARCHAR 30)**

Semantic role of this entity in the fact:

**Character roles**:
- subject, object, victim, witness, giver, receiver, attacker, defender, speaker, listener, discoverer

**Location roles**:
- scene, origin, destination, near, within, above, below

**Item roles**:
- tool, weapon, gift, disputed_object, evidence, container, contents

**Event roles**:
- caused_by, led_to, related_to, consequence_of

**Why semantic roles?**
- **Clarity**: "Who was the victim?" vs "Who was involved?"
- **Query power**: "Find all facts where Alice was a witness"
- **LLM context**: Helps LLM understand entity relationships
- **Narrative generation**: Generate appropriate descriptions based on role

**is_primary (BOOLEAN)**

Flags the "main" entity in a fact:

- **Simplifies queries**: "Find facts primarily about Alice" without complex role logic
- **Display prioritization**: Show primary entities first in UI
- **LLM focus**: Helps LLM identify the fact's main subject
- **One primary per fact**: Typically one entity is marked primary, others are supporting

**Example**: "Alice gave Bob a sword"
- Alice: is_primary=TRUE, role='giver'
- Bob: is_primary=FALSE, role='receiver'
- Sword: is_primary=FALSE, role='gift'

**relationship_strength (DECIMAL 0.0-1.0)**

How central is this entity to the fact?

- **1.0**: Core to the fact's meaning
- **0.5**: Important but not central
- **0.1**: Mentioned but peripheral

**Use cases**:
- **Query weighting**: Prioritize facts with high-strength connections
- **LLM context**: Include only high-strength relationships in limited contexts
- **Importance calculation**: Factor into fact importance scoring

**deleted_at (TIMESTAMP)**

Soft delete for relationship:

- **Why delete relationships?**: Entity may be retconned out of fact
- **History preservation**: Keep for audit trail
- **Query filtering**: Active queries use `WHERE deleted_at IS NULL`

### Fact Relationship History

```
fact_relationship_history
├── id                      INTEGER PRIMARY KEY
├── fact_history_id         INTEGER FK → fact_history.id NOT NULL
├── related_entity_type     VARCHAR(20) NOT NULL
├── related_entity_id       INTEGER NOT NULL
├── role                    VARCHAR(30)
├── is_primary              BOOLEAN DEFAULT FALSE
├── relationship_strength   DECIMAL(3,2) DEFAULT 1.0
└── created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP

CONSTRAINTS:
- related_entity_type IN ('character', 'location', 'item', 'event')
- relationship_strength BETWEEN 0.0 AND 1.0

INDEXES:
- Standard index on fact_history_id
- Composite index on (related_entity_type, related_entity_id)
```

**Purpose**: Preserve which entities were connected to each historical fact version.

When fact evolves, its relationships may change:
- "Alice and Bob fought" → "Alice, Bob, and Carol fought" (Carol added)
- "Found sword in tavern" → "Found sword in ancient ruins" (location changed)

Each FactHistory snapshot includes its own relationship snapshot, enabling perfect reconstruction of "what the world knew" at any point in time.

---

## Character Knowledge

### Concept

**CharacterKnowledge** is the subjective layer: what individual characters believe, with what confidence, learned through what means, and potentially distorted by their perspective.

**Core Principle**: Two characters can know the **same fact** with wildly different contexts:

**Example**:
```
Fact: "The Dragon God sleeps beneath the mountain"

Priest's Knowledge:
- belief_strength: 1.0
- learned_from_type: 'religious'
- personal_context: "Sacred texts confirm this divine truth"
- will_share: TRUE

Skeptic's Knowledge:
- belief_strength: 0.2
- learned_from_type: 'told_by'
- personal_context: "Old superstition with no evidence"
- will_share: FALSE
```

**Knowledge Evolution**: Characters don't just learn once—they update understanding over time:
- Rumor → firsthand observation
- Belief → doubt → disbelief
- Old information → corrected information
- Version 1 → Version 2 → Version 3

Each update creates a new knowledge entry linked via supersession chain, preserving the character's full learning journey.

### Schema

```
character_knowledge
├── id                              INTEGER PRIMARY KEY
├── character_id                    INTEGER FK → characters.id NOT NULL
├── fact_id                         INTEGER FK → facts.id NOT NULL
├── fact_history_id                 INTEGER FK → fact_history.id
├── knowledge_version               INTEGER DEFAULT 1 NOT NULL
├── is_current                      BOOLEAN DEFAULT TRUE NOT NULL
├── superseded_by_knowledge_id      INTEGER FK → character_knowledge.id
├── superseded_at                   BIGINT
├── belief_strength                 DECIMAL(3,2) DEFAULT 1.0
├── learned_from_type               VARCHAR(20)
├── learned_from_character_id       INTEGER FK → characters.id
├── learned_from_event_id           INTEGER FK → events.id
├── will_share                      BOOLEAN DEFAULT TRUE
├── learned_at                      BIGINT
├── personal_context                VARCHAR(500)
├── distortion_type                 VARCHAR(30)
├── created_at                      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
└── deleted_at                      TIMESTAMP

CONSTRAINTS:
- UNIQUE (character_id, fact_id) WHERE deleted_at IS NULL AND is_current = TRUE
- belief_strength BETWEEN 0.0 AND 1.0
- learned_from_type IN ('witness', 'told_by', 'rumor', 'deduction', 'memory', 'intuition', 'research', 'reading', 'divine_revelation')
- distortion_type IN (NULL, 'complete', 'partial', 'embellished', 'inverted', 'exaggerated', 'minimized', 'reinterpreted')
- knowledge_version > 0
- LENGTH(personal_context) <= 500
- (superseded_by_knowledge_id NOT NULL) REQUIRES (superseded_at NOT NULL)

INDEXES:
- Partial index on (character_id, fact_id) WHERE deleted_at IS NULL AND is_current = TRUE
- Partial index on character_id WHERE deleted_at IS NULL
- Partial index on fact_id WHERE deleted_at IS NULL
- Composite index on (character_id, learned_at)
- Composite index on (fact_id, belief_strength)
- Partial index on (character_id, is_current) WHERE is_current = TRUE
```

### Design Decisions

**fact_id vs fact_history_id**

Both stored to enable different query patterns:

**fact_id** (always present):
- Links to current Fact record
- Fast joins: "What does character know about this fact?"
- Primary reference for most queries

**fact_history_id** (optional):
- Links to specific FactHistory snapshot
- Captures **which version** character learned
- Enables knowledge divergence: character knows old version while current version differs

**When fact_history_id is used**:
- Character learns about location in Year 1000 → references FactHistory from 1000
- Location changes in Year 1050 → new FactHistory created
- Character's knowledge frozen at old snapshot
- Query reveals: "Character has outdated information"

**When fact_history_id is NULL**:
- Character always knows current version (knowledge auto-updates conceptually)
- Common for evergreen facts that don't change

**knowledge_version (INTEGER)**

Tracks how many times character's understanding of **this specific fact** has evolved:

- **Version 1**: Initial learning
- **Version 2**: Updated understanding  
- **Version 3**: Further correction
- **Not global**: Each character's knowledge of each fact has own version sequence

**Use case**: "Show me how Alice's understanding of the assassination evolved"
- v1: Heard rumor "Duke died naturally" (belief: 0.6)
- v2: Told by guard "Duke was murdered" (belief: 0.9)
- v3: Saw evidence "Guild member did it" (belief: 1.0)

**is_current (BOOLEAN)**

TRUE: This is character's current understanding
FALSE: This is superseded historical understanding

**Critical for queries**:
```sql
-- What does character currently believe?
WHERE character_id = X AND is_current = TRUE AND deleted_at IS NULL

-- What did character used to believe?
WHERE character_id = X AND is_current = FALSE
```

**Only one knowledge entry** per (character, fact) has `is_current = TRUE` at any time.

**superseded_by_knowledge_id (self-reference)**

Creates **knowledge evolution chains**:
```
Knowledge #1 (v1, is_current=FALSE) → supersedes → Knowledge #2
Knowledge #2 (v2, is_current=FALSE) → supersedes → Knowledge #3
Knowledge #3 (v3, is_current=TRUE)  → supersedes → NULL
```

**Traversing chain**: Walk backwards and forwards to reconstruct full learning journey.

**superseded_at (BIGINT in-game time)**

When this understanding was replaced:

- **Required if superseded**: Database enforces timestamp when superseded_by_knowledge_id is set
- **Learning timeline**: Track character's intellectual development
- **Narrative context**: "You believed that for 3 years before learning the truth"

**belief_strength (DECIMAL 0.0-1.0)**

How confident is character in this knowledge?

**1.0**: Absolutely certain (witnessed firsthand, irrefutable evidence)
**0.7-0.9**: Pretty sure (reliable source, consistent with other knowledge)
**0.4-0.6**: Uncertain (rumor, contradictory evidence, doubtful source)
**0.1-0.3**: Doubtful (probably false, but can't rule out completely)

**Gameplay implications**:
- **Dialogue generation**: "I think..." (0.5) vs "I know..." (1.0)
- **Decision making**: Low belief → character hesitates, seeks confirmation
- **Information value**: Higher belief knowledge is more valuable to trade
- **Persuasion**: Easier to change low-belief knowledge

**learned_from_type (VARCHAR 20)**

How character acquired this knowledge:

**Source types**:
- `witness`: Saw it with own eyes (usually belief_strength=1.0)
- `told_by`: Directly informed by another character (check learned_from_character_id)
- `rumor`: Heard indirectly, third-hand information (lower belief)
- `deduction`: Figured it out from other facts (logical inference)
- `memory`: Remembers from long ago (may be unreliable)
- `intuition`: Gut feeling, hunch (low belief unless character has special insight)
- `research`: Studied documents, books, records (high belief for scholars)
- `reading`: Found in specific text (depends on text reliability)
- `divine_revelation`: Religious/spiritual source (high belief for believers)

**Reliability hierarchy**: witness > told_by > research > reading > deduction > rumor > memory > intuition

**learned_from_character_id (Character FK)**

**Who** taught them (if learned_from_type = 'told_by' or 'rumor'):

- **Trust networks**: "I trust what Aldric tells me"
- **Rumor propagation**: Track who told whom
- **Interrogation**: "Who told you this?"
- **Credibility**: Does source have good track record?

**NULL for non-social learning** (witness, deduction, reading, divine_revelation)

**learned_from_event_id (Event FK)**

**What event** generated this knowledge:

- **Dialogue event**: Character learned from conversation
- **Combat event**: Character learned who won/died
- **Discovery event**: Character found hidden information
- **Revelation event**: Secret uncovered during quest

**Contextual queries**: "What did character learn during the feast?"

**will_share (BOOLEAN)**

Will character tell others about this knowledge?

**TRUE (default)**: Normal information, shares if asked or relevant
**FALSE**: Secrets, strategic advantages, oaths, embarrassing info

**Rumor propagation**: Only knowledge with `will_share=TRUE` spreads to others
**Gameplay**:
- NPC won't reveal secret unless persuaded/threatened/bribed
- Character hoards valuable information
- Conspiracy members refuse to share cover story

**learned_at (BIGINT in-game time)**

When character acquired this knowledge:

- **Timeline tracking**: Character's learning history
- **Knowledge recency**: Recent knowledge more reliable than old
- **Temporal context**: "You learned this 10 years ago"
- **Staleness**: Old knowledge may be outdated even if not superseded

**personal_context (VARCHAR 500)**

**Character's subjective interpretation** of the fact:

Even knowing **same fact**, characters add personal meaning:

```
Fact: "The bridge collapsed"

Guard: "Shoddy engineering—I always said it was unsafe"
Merchant: "This will ruin trade routes for months, disaster for profits"
Priest: "Divine punishment for the town's sins"
Bard: "What a dramatic scene! I'll compose a ballad about the tragedy"
```

**Not distortion of content**: Fact content remains same, character adds spin

**Length limit (500 chars)**: Prevents excessive LLM generation while allowing personality

**LLM integration**: Used in dialogue generation to create unique character voices and perspectives

**distortion_type (VARCHAR 30)**

**How** character's understanding differs from fact's actual content:

**NULL**: Character knows fact accurately
**complete**: Totally wrong, no resemblance to truth
**partial**: Some parts right, some parts wrong
**embellished**: True facts plus exaggerated/added details
**inverted**: Believes opposite of what's true
**exaggerated**: Amplifies magnitude (minor event → major disaster)
**minimized**: Downplays significance (major event → minor incident)
**reinterpreted**: Different causal explanation (same event, different "why")

**When to use**:

**Don't use for FALSE facts**: If character believes myth, there's no distortion—the myth IS the fact
**Use for TRUE facts misunderstood**: Character saw event but misinterpreted

**Example**:
```
TRUE Fact: "Guild member killed merchant in marketplace"

Character Knowledge:
- fact_id: (same fact)
- distortion_type: 'inverted'
- personal_context: "I'm sure it was bandits, not the guild. The guild would never."
- belief_strength: 0.8
```

**deleted_at (TIMESTAMP real-world time)**

Soft delete for knowledge:

- **Why soft delete?** Character may forget, but we preserve learning history
- **Memory limits**: Characters have knowledge_capacity, old knowledge gets deleted when capacity reached
- **Historical queries**: "What did character know in Year 1050?"
- **Psychological realism**: Memories can be "forgotten" but retrieved

**Different from is_current**: 
- `is_current=FALSE`: Superseded by new knowledge (still in active history)
- `deleted_at`: Completely removed from character's active memory

### Knowledge Evolution Methods

**get_knowledge_chain()**

Returns full evolution chain of character's understanding:

```python
# Character's learning journey:
v1: "Pass is safe" (rumor, belief=0.6)
v2: "Pass is blocked" (told_by_guard, belief=0.9)
v3: "Pass was cleared yesterday" (witness, belief=1.0)
```

**update_understanding()**

Supersedes current knowledge with new understanding:

```python
knowledge.update_understanding(
    session=db_session,
    new_fact_id=124,  # Updated fact
    learned_from_type='witness',
    learned_from_id=None
)
# Creates new knowledge entry with version+1
# Links via superseded_by_knowledge_id
# Marks old knowledge as is_current=FALSE
```

---

## System Integration

### Triple-Layer Temporal Tracking

The system tracks three levels of temporal state:

**Layer 1: Location/Entity Evolution**
- LocationHistory: Village → City
- PathHistory: Safe → Blocked → Cleared

**Layer 2: Fact Evolution**
- FactHistory: "Millbrook is a village" → "Millbrook is a city"
- Each fact snapshot references appropriate location snapshot

**Layer 3: Knowledge Evolution**
- CharacterKnowledge: Character learns "village" fact
- World changes to city, but character's knowledge stays at old fact version
- Character eventually learns "city" fact, superseding old knowledge

**Example Timeline**:
```
Year 1000:
  LocationHistory #1: "Millbrook village, 200 population"
  Fact #1: "Millbrook is a village" → references LocationHistory #1
  Character learns Fact #1

Year 1050:
  LocationHistory #2: "Millbrook city, 12,000 population"
  Fact #2: "Millbrook is a city" → references LocationHistory #2
  Character still knows Fact #1 (outdated)

Year 1075:
  Character visits Millbrook
  LLM: "You're surprised to find Millbrook has grown into a bustling city..."
  Character learns Fact #2, superseding knowledge of Fact #1
```

### Knowledge Divergence Gameplay

The triple-layer system enables emergent gameplay:

**Outdated Directions**:
- Old merchant: "Take the mountain pass, it's perfectly safe" (Year 1000 knowledge)
- Current reality: Pass blocked by avalanche (Year 1050 event)
- Player follows directions, discovers avalanche
- Quest: Return to merchant with updated information

**Urban Development**:
- Scholar's map: "Millbrook - small village, good rest stop" (Year 1025 knowledge)
- Player arrives: Thriving city of 12,000 with walls and guards
- Opportunity: Sell updated maps to travelers
- Quest: Document city growth for royal cartographers

**Information as Currency**:
- Characters with recent, accurate knowledge have valuable commodity
- Outdated knowledge becomes liability
- Information brokers track who knows what
- Espionage: Plant false information, track its spread

### Fact Categories and Truth Constraints

The category system prevents accidental false facts while enabling intentional cultural narratives:

**Creating TRUE facts** (observed reality):
```python
fact = Fact(
    content="The northern bridge collapsed during the storm",
    fact_category='observed',  # Must be TRUE category
    canonical_truth=True,  # Automatically set based on category
    when_occurred=current_game_time
)
```

**Creating FALSE facts** (myths/conspiracies):
```python
fact = Fact(
    content="The Dragon God sleeps beneath Frostpeak Mountain",
    fact_category='myth',  # Must be FALSE category
    canonical_truth=False,  # Automatically set based on category
    created_by_character_id=elder_shaman_id  # REQUIRED by constraint
)
```

**Database prevents mixing**:
```python
# This will FAIL - constraint violation:
Fact(
    content="...",
    fact_category='myth',  # FALSE category
    canonical_truth=True   # Can't be TRUE
)
```

### Knowledge Evolution Chains

Character understanding evolves through supersession:

**Stage 1: Rumor** (Year 1000)
```python
Knowledge #1:
- fact: "Pass is safe for travel"
- version: 1
- is_current: FALSE (later superseded)
- belief_strength: 0.6
- learned_from_type: 'rumor'
- personal_context: "Heard from tavern gossip"
```

**Stage 2: Authoritative Update** (Year 1025)
```python
Knowledge #2:
- fact: "Pass is blocked by avalanche"
- version: 2
- is_current: FALSE (later superseded)
- belief_strength: 1.0
- learned_from_type: 'told_by'
- learned_from_character: reliable_scout
- personal_context: "Scout saw it with own eyes"
- Knowledge #1.superseded_by_knowledge_id → #2
```

**Stage 3: Firsthand Verification** (Year 1050)
```python
Knowledge #3:
- fact: "Pass has been cleared by engineers"
- version: 3
- is_current: TRUE
- belief_strength: 1.0
- learned_from_type: 'witness'
- personal_context: "I watched the clearing crew finish"
- Knowledge #2.superseded_by_knowledge_id → #3
```

**Query the chain**:
```python
chain = knowledge_3.get_knowledge_chain()
# Returns: [Knowledge #1, Knowledge #2, Knowledge #3]

# Character's belief evolution narrative:
# "I heard the pass was safe" →
# "I learned it was blocked" →
# "I saw them clear it myself"
```

### Cultural Narratives

**Shared myths as cultural objects**:

**Northern Mountains Culture**:
```python
Fact: "The Dragon God sleeps beneath Frostpeak"
- fact_category: 'myth'
- canonical_truth: FALSE
- created_by_character: elder_shaman

# 200 NPCs know this myth:
CharacterKnowledge (×200):
- belief_strength: 0.9-1.0 (strong cultural belief)
- learned_from_type: 'religious' or 'cultural'
- will_share: TRUE
```

**Southern Desert Culture** (different myth about same location):
```python
Fact: "Frostpeak was raised by ancient earth-mages"
- fact_category: 'legend'
- canonical_truth: FALSE
- created_by_character: desert_historian

# 150 NPCs in southern region know this version
```

**Gameplay**:
- Northerner tells player: Dragon God story
- Southerner tells player: Earth-mage story
- Both believe their version completely
- Quest: Discover which (if either) is true
- Cultural identity through belief systems

### Conspiracy Mechanics

**Coordinated lies as shared FALSE facts**:

```python
# TRUE fact (what actually happened):
Fact #1:
- content: "Guild assassin murdered Merchant Aldric"
- category: 'observed'
- canonical_truth: TRUE

# FALSE fact (conspiracy cover story):
Fact #2:
- content: "Bandits killed Merchant Aldric on the road"
- category: 'conspiracy'
- canonical_truth: FALSE
- created_by_character: guild_master

# 8 conspirators know false fact:
CharacterKnowledge (×8):
- fact: Fact #2
- belief_strength: 1.0
- learned_from_type: 'conspiracy'
- will_share: TRUE  # Actively spreading the lie

# Witness knows truth:
CharacterKnowledge (guard):
- fact: Fact #1
- belief_strength: 1.0
- learned_from_type: 'witness'
- will_share: FALSE  # Afraid to contradict guild
```

**Detective Gameplay**:
- Multiple NPCs tell same story (suspicious consistency)
- Witness knows different version but won't share
- Player must gain trust or intimidate to get truth
- Cross-reference: Who benefits from the lie?

### Rumor Propagation

Information spreads through social network with degradation:

```python
# Source character knows fact:
source_knowledge = CharacterKnowledge(
    fact: "Guild meeting tonight at midnight",
    belief_strength: 1.0,
    will_share: TRUE,
    learned_from_type: 'witness'
)

# Propagate to 5 other characters:
propagate_rumor(
    source_knowledge_id=source.id,
    target_character_ids=[char1, char2, char3, char4, char5],
    distortion_chance=0.3,  # 30% chance of distortion
    belief_decay=0.1        # Each hop reduces belief by 0.1
)

# Results (probabilistic):
Char1: belief=0.9, distortion=None
Char2: belief=0.9, distortion='embellished' ("secret guild meeting")
Char3: belief=0.9, distortion=None
Char4: belief=0.9, distortion='exaggerated' ("emergency guild meeting")
Char5: belief=0.9, distortion='partial' ("guild meeting tonight" - time lost)
```

**Emergent "Telephone Game"**: Information degrades through network, creating organic misinformation.

### Fact Importance and Cleanup

**Importance scoring prevents fact explosion**:

```python
def update_importance(fact):
    # Count active knowledge references
    knowledge_count = count(fact.character_knowledge WHERE deleted_at IS NULL)
    
    # Time decay factor
    days_since_reference = (current_time - fact.last_referenced) / 86400
    time_decay = min(1.0, 30.0 / max(1.0, days_since_reference))
    
    # Calculate score
    fact.importance_score = min(1.0, (knowledge_count * 0.1) * time_decay)
```

**Cleanup job** (runs periodically):
```python
def cleanup_unimportant_facts(session):
    # Find facts meeting criteria:
    # - importance_score < 0.1
    # - last_referenced > 30 days ago
    # - No active knowledge references
    
    facts = query_unimportant_facts()
    
    for fact in facts:
        # Soft delete all knowledge
        for knowledge in fact.character_knowledge:
            knowledge.deleted_at = current_timestamp()
        
        # Could hard-delete fact, but keeping for historical queries
```

### Character Memory Limits

Characters have finite memory capacity:

```python
class Character:
    knowledge_capacity = Column(Integer, default=1000)

def prune_character_knowledge(character):
    # Get all active knowledge, ranked by importance and recency
    knowledge = get_knowledge_ranked(character.id)
    
    # Keep only top N facts
    capacity = character.knowledge_capacity
    
    # Soft delete everything beyond capacity
    for k in knowledge[capacity:]:
        k.deleted_at = current_timestamp()
```

**Natural forgetting**:
- Old, unimportant facts get pruned
- High-importance facts persist longer
- Recently referenced facts prioritized
- Psychological realism: limited memory

---

## DeepAgent Workflows

The epistemic engine leverages DeepAgents for autonomous reasoning about facts, knowledge, and belief evolution. Here's how agents integrate with the database schema:

### Fact Decomposition Workflow

**Agent**: `fact_decomposition_agent.py`

**Input**: Natural language description
```
"Alice gave Bob a sword in the tavern after defeating the bandits"
```

**Agent Process**:
1. Parse text → identify atomic propositions
2. For each fact:
   - Determine `canonical_truth` (TRUE/FALSE)
   - Assign `fact_category` (observed, historical, myth, etc.)
   - Extract `what_type` (combat, transfer, etc.)
   - Write `why_context` with causal explanation
3. Create `FactRelationships` with semantic roles
4. Use `validate_fact_consistency` tool to check contradictions

**Database Output**:
```sql
-- Fact 1
INSERT INTO facts (content, fact_category, canonical_truth, what_type, when_occurred)
VALUES ('Alice defeated the bandit group', 'observed', TRUE, 'combat', <timestamp>);

INSERT INTO fact_relationships (fact_id, related_entity_type, related_entity_id, role)
VALUES
  (<fact1_id>, 'character', <alice_id>, 'attacker'),
  (<fact1_id>, 'character', <bandit_id>, 'victim');

-- Fact 2
INSERT INTO facts (content, fact_category, canonical_truth, what_type)
VALUES ('Alice gave Bob a sword', 'observed', TRUE, 'transfer');

INSERT INTO fact_relationships (fact_id, related_entity_type, related_entity_id, role)
VALUES
  (<fact2_id>, 'character', <alice_id>, 'giver'),
  (<fact2_id>, 'character', <bob_id>, 'receiver'),
  (<fact2_id>, 'item', <sword_id>, 'gift'),
  (<fact2_id>, 'location', <tavern_id>, 'scene');
```

---

### Knowledge Evolution Workflow

**Agent**: `knowledge_evolution_agent.py`

**Scenario**: Character learns new information that contradicts existing belief

**Agent Process**:
1. Query existing knowledge: `SELECT * FROM character_knowledge WHERE character_id = X AND fact_id = Y AND is_current = TRUE`
2. Evaluate source reliability (witness > told_by > rumor > memory)
3. Compare new vs. old information
4. Calculate new `belief_strength` based on source + character personality
5. Determine if `distortion_type` applies (based on character biases)
6. Create supersession chain

**Database Output**:
```sql
-- Mark old knowledge as superseded
UPDATE character_knowledge
SET is_current = FALSE,
    superseded_by_knowledge_id = <new_knowledge_id>,
    superseded_at = <current_game_time>
WHERE id = <old_knowledge_id>;

-- Create new knowledge version
INSERT INTO character_knowledge (
  character_id, fact_id, knowledge_version, is_current,
  belief_strength, learned_from_type, personal_context
)
VALUES (
  <character_id>, <fact_id>, 2, TRUE,
  0.9, 'witness', 'I saw it with my own eyes'
);
```

**Result**: Character knowledge version chain preserved:
- Version 1 (superseded): "Pass is safe" (rumor, belief=0.6)
- Version 2 (current): "Pass is blocked" (witness, belief=1.0)

---

### Rumor Propagation Workflow

**Agent**: `rumor_propagation_agent.py`

**Scenario**: Information spreads through social network A→B→C→D with degradation

**Agent Process**:
1. Get source knowledge (must have `will_share = TRUE`)
2. For each target in propagation list:
   - Calculate `belief_strength = source_belief - (decay_factor * hop_count)`
   - Roll distortion probability (increases with hops)
   - Determine `distortion_type` based on character personality
   - Create `CharacterKnowledge` with `learned_from_character_id` chain

**Database Output**:
```sql
-- Hop 1: A→B (30% distortion chance)
INSERT INTO character_knowledge (
  character_id, fact_id, belief_strength,
  learned_from_type, learned_from_character_id,
  distortion_type, personal_context
)
VALUES (
  <B_id>, <fact_id>, 0.9,
  'told_by', <A_id>,
  NULL, 'A told me directly'
);

-- Hop 2: B→C (45% distortion chance, distortion occurred)
INSERT INTO character_knowledge (
  character_id, fact_id, belief_strength,
  learned_from_type, learned_from_character_id,
  distortion_type, personal_context
)
VALUES (
  <C_id>, <fact_id>, 0.8,
  'told_by', <B_id>,
  'embellished', 'Heard it was an emergency meeting, not just a regular one'
);

-- Hop 3: C→D (60% distortion chance, detail lost)
INSERT INTO character_knowledge (
  character_id, fact_id, belief_strength,
  learned_from_type, learned_from_character_id,
  distortion_type, personal_context
)
VALUES (
  <D_id>, <fact_id>, 0.7,
  'rumor', <C_id>,
  'partial', 'Something about a meeting tonight, not sure when exactly'
);
```

**Result**: Emergent "telephone game" with believable information degradation.

---

### Temporal State Coordination Workflow

**Agent**: `temporal_state_coordinator.py`

**Scenario**: Millbrook grows from village (Year 1000) to city (Year 1050)

**Agent Process**:
1. Close current LocationHistory: `UPDATE location_history SET valid_to = 1050 WHERE location_id = X AND valid_to IS NULL`
2. Create new LocationHistory snapshot with updated population, description
3. Find Facts referencing old LocationHistory
4. Create FactHistory preserving old snapshots
5. Update current Facts to reference new LocationHistory (if fact still true) OR create superseding facts
6. Identify CharacterKnowledge referencing outdated FactHistory
7. Log characters with outdated knowledge (DO NOT auto-update - drives gameplay)

**Database Output**:
```sql
-- 1. Close old location snapshot
UPDATE location_history
SET valid_to = 1050
WHERE location_id = <millbrook_id> AND valid_to IS NULL;

-- 2. Create new location snapshot
INSERT INTO location_history (
  location_id, name, population, description,
  valid_from, valid_to
)
VALUES (
  <millbrook_id>, 'Millbrook', 12000, 'A bustling city with high walls...',
  1050, NULL
);

-- 3. Archive old fact
INSERT INTO fact_history (
  fact_id, content, where_location_history_id,
  valid_from, valid_to, change_reason
)
VALUES (
  <fact_id>, 'Millbrook is a quiet village',
  <old_location_history_id>,
  1000, 1050, 'Village grew into city due to trade boom'
);

-- 4. Create superseding fact
UPDATE facts
SET superseded_by_fact_id = <new_fact_id>,
    superseded_at = 1050
WHERE id = <old_fact_id>;

INSERT INTO facts (
  content, where_location_history_id, fact_category, canonical_truth
)
VALUES (
  'Millbrook is a thriving city of 12,000 people',
  <new_location_history_id>, 'current_state', TRUE
);

-- 5. Character knowledge remains pointing to old FactHistory (outdated!)
-- Query to find affected characters:
SELECT DISTINCT ck.character_id
FROM character_knowledge ck
JOIN facts f ON ck.fact_id = f.id
WHERE f.id = <old_fact_id> AND ck.is_current = TRUE;
```

**Result**:
- World state updated with historical continuity
- Facts preserve temporal snapshots
- Characters with outdated knowledge identified for gameplay opportunities
- Agent suggests discovery events: "Character X should visit Millbrook and be surprised"

---

### Myth Creation Workflow

**Agent**: `myth_creation_agent.py`

**Scenario**: Create regional myth about mountain

**Agent Process**:
1. Determine appropriate `fact_category` (myth, legend, prophecy, conspiracy, etc.)
2. Identify creator character (elder shaman, priest, bard, conspiracy leader)
3. Write compelling `content` (not generic)
4. Explain `why_context` (cultural origin and purpose)
5. Optionally link to TRUE facts (legends based on real events)
6. Ensure database constraints satisfied:
   - `canonical_truth = FALSE`
   - `created_by_character_id NOT NULL`
   - Category matches FALSE categories

**Database Output**:
```sql
INSERT INTO facts (
  content, fact_category, canonical_truth,
  created_by_character_id, why_context, what_type
)
VALUES (
  'The Dragon God Kethraxi sleeps beneath Frostpeak Mountain, and her dreams shape the winter storms',
  'myth', FALSE,
  <elder_shaman_id>,
  'This myth arose to explain the unusual severity and unpredictability of storms near Frostpeak. The elder shamans formalized it into religious doctrine 300 years ago.',
  'religious'
);

-- Relationship to location
INSERT INTO fact_relationships (fact_id, related_entity_type, related_entity_id, role)
VALUES (<myth_fact_id>, 'location', <frostpeak_id>, 'scene');

-- 200 NPCs now believe this myth
INSERT INTO character_knowledge (character_id, fact_id, belief_strength, learned_from_type)
SELECT id, <myth_fact_id>, 0.95, 'cultural'
FROM characters
WHERE region = 'Northern Mountains';
```

**Result**: Shared cultural narrative with proper constraints, spread among regional population.

---

### Character Belief Reasoning Workflow

**Agent**: `character_belief_agent.py`

**Scenario**: Determine if character accepts new information

**Agent Process**:
1. Get character's existing knowledge on topic
2. Analyze personality traits (skeptical, gullible, biased, logical, dramatic, paranoid)
3. Evaluate source reliability and trust relationship
4. Check for contradictions with existing beliefs
5. Determine: accept, reject, or distort
6. Calculate `belief_strength` based on source quality + personality
7. Apply `distortion_type` if personality biases affect interpretation
8. Decide if supersession needed

**Example - Skeptical Character**:
```sql
-- Input: Rumor about dragon (low reliability source)
-- Character personality: Skeptical

-- Agent decision: Accept with low belief, minimize distortion
INSERT INTO character_knowledge (
  character_id, fact_id, belief_strength,
  learned_from_type, distortion_type, personal_context
)
VALUES (
  <skeptic_id>, <dragon_fact_id>, 0.2,
  'rumor', 'minimized',
  'Probably just a large lizard someone saw. People exaggerate.'
);
```

**Example - Gullible Character**:
```sql
-- Same input: Rumor about dragon
-- Character personality: Gullible

-- Agent decision: Accept with high belief, possible embellishment
INSERT INTO character_knowledge (
  character_id, fact_id, belief_strength,
  learned_from_type, distortion_type, personal_context
)
VALUES (
  <gullible_id>, <dragon_fact_id>, 0.8,
  'rumor', 'embellished',
  'Not just any dragon - a HUGE one! They say it destroyed entire villages!'
);
```

**Result**: Same fact, two characters, vastly different beliefs - driven by personality simulation.

---

### Game Master Narrative Generation Workflow

**Agent**: `game_master_agent.py`

**Scenario**: Player asks NPC about Millbrook

**Agent Process**:
1. Identify speaking character
2. Query `character_knowledge` for that character's beliefs about Millbrook
3. Check `belief_strength` (affects confidence in speech)
4. Check `distortion_type` (affects description accuracy)
5. Check if `fact_history_id` points to outdated snapshot
6. Generate NPC dialogue reflecting THEIR knowledge
7. Generate GM narration revealing knowledge divergence

**Database Query**:
```sql
SELECT
  ck.belief_strength,
  ck.distortion_type,
  ck.personal_context,
  f.content,
  fh.content as historical_content,
  fh.valid_to as fact_outdated_at
FROM character_knowledge ck
JOIN facts f ON ck.fact_id = f.id
LEFT JOIN fact_history fh ON ck.fact_history_id = fh.id
WHERE ck.character_id = <npc_id>
  AND f.id IN (SELECT fact_id FROM fact_relationships
               WHERE related_entity_type = 'location'
               AND related_entity_id = <millbrook_id>)
  AND ck.is_current = TRUE
  AND ck.deleted_at IS NULL;
```

**Agent Output**:
```json
{
  "npc_dialogue": "Millbrook? Oh yes, peaceful little village. Good place to rest for the night. I was there about... oh, 20 years ago now. Lovely quiet spot.",
  "narration": "As you approach Millbrook, you're surprised to find high stone walls and the bustle of a major city. Guard towers flank the gates, and merchant stalls line crowded streets. It seems much has changed since your informant last visited.",
  "knowledge_used": [
    {
      "fact_id": 142,
      "belief_strength": 1.0,
      "is_outdated": true,
      "historical_content": "Millbrook is a quiet village",
      "current_reality": "Millbrook is a thriving city"
    }
  ]
}
```

**Result**: Narrative reveals knowledge divergence organically, creating discovery moment for player.

---

## Design Principles Summary

**1. Epistemological Integrity**
- Objective reality (Facts) separated from subjective belief (Knowledge)
- Truth is persistent, belief is fluid
- Characters can be wrong, outdated, or deceived
- Information asymmetry drives gameplay

**2. Temporal Depth**
- Facts evolve through FactHistory
- Knowledge evolves through version chains
- Location/Fact/Knowledge triple-layer tracking
- Full reconstruction of information state at any point in time

**3. Cultural Simulation**
- Shared false facts as cultural objects
- Myths, legends, religions independent of individuals
- Regional belief systems through distributed knowledge
- Narrative identity through community beliefs

**4. Intentional Complexity**
- FALSE facts require explicit categorization (prevents accidents)
- Mandatory creators for cultural narratives (accountability)
- Distortion for individual misunderstanding (cleaner model)
- Category constraints enforce design philosophy

**5. Scalability Through Pruning**
- Importance scoring prevents fact explosion
- Automated cleanup of unreferenced facts
- Character memory limits prevent knowledge bloat
- Soft deletes preserve history without bloating active queries

**6. LLM-Native Design**
- Natural language content fields
- Categorical tags for context filtering
- Rich narrative metadata (why_context, personal_context)
- Chain traversal for explaining belief evolution
- Semantic roles for entity relationships

**7. Emergent Gameplay**
- Detective work: Cross-reference contradictory knowledge
- Trust networks: Who told whom, reliability chains
- Cultural exchange: Different regions, different beliefs
- Archaeological quests: Discover truth behind myths
- Information as power: Knowledge is valuable currency

**8. Narrative Causality**
- Events generate Facts
- Facts become Knowledge
- Knowledge influences Dialogue
- Dialogue creates new Events
- Complete narrative cycle through relational chains

---

## Query Patterns

**"What does this character currently believe?"**
```sql
SELECT f.* FROM facts f
JOIN character_knowledge ck ON f.id = ck.fact_id
WHERE ck.character_id = ?
  AND ck.is_current = TRUE
  AND ck.deleted_at IS NULL
```

**"What is objectively true about this location?"**
```sql
SELECT f.* FROM facts f
JOIN fact_relationships fr ON f.id = fr.fact_id
WHERE fr.related_entity_type = 'location'
  AND fr.related_entity_id = ?
  AND f.canonical_truth = TRUE
  AND fr.deleted_at IS NULL
```

**"What myths exist in this region?"**
```sql
SELECT f.*, COUNT(ck.id) as believer_count
FROM facts f
JOIN fact_relationships fr ON f.id = fr.fact_id
JOIN character_knowledge ck ON f.id = ck.fact_id
JOIN characters c ON ck.character_id = c.id
WHERE f.canonical_truth = FALSE
  AND f.fact_category IN ('myth', 'legend', 'religious')
  AND fr.related_entity_type = 'location'
  AND fr.related_entity_id IN (locations_in_region)
  AND ck.is_current = TRUE
  AND ck.deleted_at IS NULL
GROUP BY f.id
HAVING COUNT(ck.id) >= 3
ORDER BY believer_count DESC
```

**"Who knows outdated information?"**
```sql
SELECT c.*, ck.*, f_old.content as old_belief, f_new.content as current_reality
FROM character_knowledge ck
JOIN characters c ON ck.character_id = c.id
JOIN facts f_old ON ck.fact_id = f_old.id
JOIN facts f_new ON f_old.superseded_by_fact_id = f_new.id
WHERE ck.is_current = TRUE
  AND ck.deleted_at IS NULL
  AND f_old.superseded_by_fact_id IS NOT NULL
```

**"How did this character's understanding evolve?"**
```sql
-- Get knowledge chain for specific character and fact
WITH RECURSIVE knowledge_chain AS (
  -- Find earliest version (no supersedes relationship)
  SELECT * FROM character_knowledge
  WHERE character_id = ?
    AND fact_id = ?
    AND NOT EXISTS (
      SELECT 1 FROM character_knowledge ck2
      WHERE ck2.superseded_by_knowledge_id = character_knowledge.id
    )
  
  UNION ALL
  
  -- Walk forward through chain
  SELECT ck.* FROM character_knowledge ck
  JOIN knowledge_chain kc ON ck.id = kc.superseded_by_knowledge_id
)
SELECT * FROM knowledge_chain
ORDER BY knowledge_version ASC
```

**"Find all facts about entity with specific role"**
```sql
SELECT f.* FROM facts f
JOIN fact_relationships fr ON f.id = fr.fact_id
WHERE fr.related_entity_type = 'character'
  AND fr.related_entity_id = ?
  AND fr.role = 'victim'
  AND fr.deleted_at IS NULL
ORDER BY f.when_occurred DESC
```

**"What facts need cleanup?"**
```sql
SELECT f.* FROM facts f
LEFT JOIN character_knowledge ck
  ON f.id = ck.fact_id
  AND ck.is_current = TRUE
  AND ck.deleted_at IS NULL
WHERE f.importance_score < 0.1
  AND f.last_referenced < (EXTRACT(EPOCH FROM NOW()) - 2592000)  -- 30 days
  AND ck.id IS NULL  -- No active knowledge references
```

---

This system creates a **living epistemological ecosystem** where truth, belief, culture, and time interweave to generate emergent narrative complexity. The triple-layer temporal tracking enables sophisticated gameplay around information asymmetry, while the semantic role system provides rich context for LLM narrative generation.