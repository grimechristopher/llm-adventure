# Core Philosophy

The game is heavily based on **facts** and the **interpretation of facts**. History and change of facts needs to be tracked and closely managed. Characters possess imperfect, potentially outdated knowledge about the world. The database must support:

1. **Temporal State Tracking**: The world changes over time; locations evolve, paths are destroyed or discovered
2. **Character Knowledge Divergence**: Different characters may know different versions of reality based on when they learned information
3. **Spatial Queries**: Efficient geographic queries for proximity, visibility, and pathfinding
4. **Emergent Narrative**: The LLM generates context-aware responses based on character knowledge, not omniscient world state
5. **Hybrid Movement**: Players can follow established paths OR travel freely through wilderness

---

## DeepAgent Architecture

The epistemic engine is powered by **LangChain DeepAgents** - autonomous reasoning agents that handle complex, multi-step operations beyond simple LCEL chains.

### Why DeepAgents?

The sophisticated triple-layer temporal tracking system (Location→Fact→Knowledge) requires reasoning capabilities that simple LLM chains cannot provide:

- **Tool Use**: Agents query the database, perform PostGIS calculations, validate consistency
- **Extended Reasoning**: Multi-step analysis for belief updates, rumor propagation, temporal coordination
- **Sub-Agent Delegation**: Complex workflows decompose into specialized sub-tasks
- **Planning & Memory**: Agents track progress through long-running operations
- **Reflection**: Iterative refinement until constraints satisfied

### Agent Categories

**World-Building Agents** (Phase 1-3):
- **Wizard Completion Agent**: Evaluates world quality with extended reasoning
- **Spatial Planner Agent**: Resolves complex geographic constraints ("between A and B, near coast")
- **Semantic Evaluator Agent**: Detects vague responses beyond keyword matching

**Epistemic Engine Agents** (Phase 5):
- **Fact Decomposition Agent**: Extracts atomic facts with semantic relationships from natural language
- **Knowledge Evolution Agent**: Manages character belief version chains with supersession tracking
- **Rumor Propagation Agent**: Models information spread through social networks with degradation
- **Temporal State Coordinator**: Orchestrates Location→Fact→Knowledge history cascades
- **Myth Creation Agent**: Generates FALSE facts (myths, legends, conspiracies) with proper constraints
- **Character Belief Reasoner**: Theory of mind for how characters accept/reject/distort information
- **Game Master Agent**: Generates narrative from character knowledge, not omniscient facts

### Agent vs. Simple Chain Decision

**Use DeepAgent when**:
- Task requires multiple steps with intermediate decisions
- Need to query database + reason about results
- Complex constraints must be satisfied
- Iterative refinement needed
- Sub-tasks should be delegated

**Use Simple LCEL Chain when**:
- Single-pass extraction (text → structured output)
- No tool calling required
- Fast response critical
- No iterative reasoning needed

### Integration with Epistemic System

DeepAgents are the **autonomous reasoning layer** on top of the **persistent knowledge layer**:

```
Player Input
    ↓
[DeepAgents Layer]
    ├─ Fact Decomposition Agent → Extracts atomic facts
    ├─ Spatial Planner Agent → Assigns coordinates
    ├─ Knowledge Evolution Agent → Updates character beliefs
    ├─ Rumor Propagation Agent → Spreads information through network
    └─ Game Master Agent → Generates narrative responses
    ↓
[Database Layer]
    ├─ LocationHistory (Layer 1: World state snapshots)
    ├─ FactHistory (Layer 2: Objective reality snapshots)
    └─ CharacterKnowledge (Layer 3: Subjective beliefs)
    ↓
Player Narrative Output
```

**Key Principle**: Agents reason about knowledge, database stores results. Separation of concerns enables:
- Complex reasoning without polluting database
- Fast queries of pre-computed results
- Auditable decision trails (agent logs)
- Iterative improvement of agent logic without schema changes

---
