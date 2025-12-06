# Intelligent Wizard - Vagueness Detection Example

## Overview

The wizard now uses **LLM-driven intelligent questioning** to detect vague responses and ask targeted follow-up questions until sufficient detail is gathered.

## How It Works

### 1. Stage Completion Evaluation (LLM-Driven)

Instead of simple rule-based checks ("≥2 facts"), the system now:

1. **Checks minimum threshold** (≥2 facts for world_identity, ≥3 locations for locations stage)
2. **Uses LLM to evaluate quality** of gathered information
3. **Detects vagueness** and identifies missing elements
4. **Returns targeted suggestions** for what to ask next

**Code Location:** `api/services/world_building_service.py:_is_stage_complete()`

### 2. Intelligent Follow-Up Questions (LLM-Driven)

Instead of generic prompts ("Tell me more..."), the system now:

1. **Analyzes the conversation history** to see what user said
2. **Uses LLM to generate targeted questions** based on gaps
3. **Probes for specificity** when responses are vague
4. **Builds on previous answers** for natural flow

**Code Location:** `api/services/world_building_service.py:_generate_follow_up_question()`

### 3. Vagueness Detection in Prompts

The wizard question agent's prompt explicitly teaches the LLM to:

- **Detect vague responses**: "fantasy world" vs "high fantasy with unstable magic"
- **Ask for specifics**: Where? How? Why? What makes it unique?
- **Provide helpful examples** to guide users

**Code Location:** `api/agents/world_builder.py:WIZARD_QUESTION_PROMPT`

---

## Example Conversation Flow

### Scenario 1: Vague World Identity

**Wizard:** "Let's start building your world! What kind of world do you want to create? Tell me about the genre, tone, and core concept."

**User:** "A fantasy world with magic"

**System Analysis:**
- Extracts: 1 fact ("Fantasy world with magic")
- Evaluates: Too vague, missing details about magic, setting, conflicts
- Decision: Ask follow-up question

**Wizard:** "That's a great start! Can you tell me more about how magic works in your world? Is it common or rare? Does it have a cost? What can magic users do?"

**User:** "Magic is rare and corrupts those who use it. It can warp reality but users gradually lose their humanity."

**System Analysis:**
- Extracts: 3 facts (magic is rare, corrupts users, warps reality)
- Evaluates: Good detail on magic system
- Decision: Still need world setting/context

**Wizard:** "Fascinating magic system! Now tell me about the world itself - is it a medieval kingdom? Floating islands? Post-apocalyptic? What's the key conflict or tension in this world?"

**User:** "Floating sky islands separated by toxic mist below. Ancient civilization collapsed when magic went unstable."

**System Analysis:**
- Extracts: 4 facts (floating islands, toxic mist, ancient collapse, unstable magic)
- Evaluates: ✅ Sufficient world identity (genre, setting, magic system, history)
- Decision: Advance to locations stage

---

### Scenario 2: Vague Location Descriptions

**Wizard:** "Great! Now tell me about the key locations in your world. Describe 3-5 important places with their spatial relationships."

**User:** "There's a capital city, a forest, and some mountains."

**System Analysis:**
- Extracts: 3 locations (capital city, forest, mountains)
- Evaluates: ❌ No spatial relationships, no specific names, too generic
- Decision: Ask for specifics

**Wizard:** "Good start! Let's add more detail. What's the capital city called? Where is it located - at the center of the islands, on a large island, or somewhere else? And how do the forest and mountains relate to it spatially?"

**User:** "The capital is called Skyreach, it's at the center. Far to the north is Frostpeak mountain. The Verdant Forest is south of Skyreach."

**System Analysis:**
- Extracts: 3 locations with names and spatial relationships
  - Skyreach (capital, center)
  - Frostpeak (mountain, far north)
  - Verdant Forest (forest, south of Skyreach)
- Evaluates: ✅ Named locations with clear spatial relationships
- Decision: Check if ready to advance

**Wizard (Completion Evaluation):**
- Locations: 3 (meets minimum)
- Quality: Names ✅, Spatial relationships ✅, Details moderate
- Decision: Could use 1-2 more locations for richness

**Wizard:** "Excellent! Those are great starting locations. Are there any other important places? Maybe a village, outpost, or point of interest between these major locations?"

**User:** "Between Skyreach and Frostpeak there's Ironhold, a mining colony."

**System Analysis:**
- Extracts: 1 more location (Ironhold, mining colony, between Skyreach and Frostpeak)
- Evaluates: ✅ 4 locations total, good spatial distribution
- Decision: Advance to next stage (if culture stage exists) or complete

---

### Scenario 3: Rejecting Insufficient Detail

**User:** "A world"

**System Analysis:**
- Extracts: 0 facts (no extractable information)
- Evaluates: ❌ Completely insufficient
- Decision: Ask clarifying question

**Wizard:** "I'd love to help you build this world! Can you tell me a bit more? What kind of world is it - fantasy, sci-fi, post-apocalyptic? What makes it interesting or unique?"

**User:** "Fantasy"

**System Analysis:**
- Extracts: 1 fact (fantasy genre)
- Evaluates: ❌ Still too vague, need setting and details
- Decision: Probe deeper

**Wizard:** "Great! Fantasy worlds can be so diverse. Is this a medieval kingdom setting? A world of floating islands? Dark fantasy with monsters? And what role does magic play, if any?"

---

## Configuration

### Minimum Thresholds (Failsafe)

These are **minimum** requirements before LLM evaluation even runs:

```python
min_thresholds = {
    'world_identity': 2,  # At least 2 facts
    'locations': 3,       # At least 3 locations
}
```

If these aren't met, the wizard **automatically** asks follow-up questions.

### LLM Evaluation Criteria

The LLM checks for **quality and specificity**:

**World Identity:**
- ❌ Vague: "fantasy world", "world with magic"
- ✅ Specific: "high fantasy with unstable ancient magic on floating sky islands"

**Locations:**
- ❌ Vague: "a city, a forest, a mountain"
- ✅ Specific: "Skyreach capital at center, Frostpeak far north, Verdant Forest south"

**Magic/Tech:**
- ❌ Vague: "magic exists"
- ✅ Specific: "magic is rare, corrupts users, can warp reality"

### Fallback Behavior

If the LLM fails (API error, timeout, etc.), the system falls back to simple rule-based logic:

1. Check minimum thresholds
2. Use generic follow-up questions
3. Log error for debugging

This ensures the wizard always works even if LLM calls fail.

---

## Benefits

### 1. **Handles Vague Users**
- Detects when responses lack detail
- Asks targeted questions to fill gaps
- Guides users to be specific without being pushy

### 2. **Quality Control**
- Rejects generic descriptions
- Ensures spatial relationships for locations
- Demands specific details about magic/tech systems

### 3. **Natural Conversation**
- Builds on previous answers
- Doesn't repeat questions
- Uses encouraging language
- Adapts to user's style

### 4. **Flexible Requirements**
- LLM can adapt evaluation criteria
- Not rigidly bound to "exactly 3 locations"
- Can recognize when 2 well-detailed locations > 5 vague ones

### 5. **Debugging Support**
- Logs LLM evaluation results
- Shows what elements are missing
- Provides feedback for improving prompts

---

## Technical Implementation

### LLM Chains Used

1. **Wizard Question Chain** (`create_wizard_question_chain`)
   - Input: stage, questions_asked, gathered_data
   - Output: WizardQuestionResponse (question_text, question_type, context_hint)

2. **Completion Evaluator Chain** (`create_wizard_completion_evaluator_chain`)
   - Input: gathered_data
   - Output: CompletionEvaluation (is_complete, missing_elements, next_suggestion)

### Service Methods

```python
# In WizardOrchestrationService

async def _is_stage_complete(self, session):
    """Uses LLM to evaluate if stage has enough detail"""
    evaluation = await self.completion_chain.ainvoke({
        "gathered_data": str(session.gathered_data)
    })
    return evaluation.is_complete

async def _generate_follow_up_question(self, session):
    """Uses LLM to generate targeted follow-up based on gaps"""
    result = await self.question_chain.ainvoke({
        "stage": stage,
        "questions_asked": len(assistant_messages),
        "gathered_data": str(session.gathered_data)
    })
    return result.question_text
```

### Flow Diagram

```
User Response
    ↓
Extract Data (LLM)
    ↓
Update gathered_data (JSONB)
    ↓
Check Minimum Threshold
    ↓ (if met)
Evaluate Quality (LLM)
    ↓
Is Complete? ──No──→ Generate Follow-Up Question (LLM)
    ↓ Yes                    ↓
Advance Stage           Ask Question
    ↓                        ↓
Next Stage Question    User Responds
                            ↓
                      (Loop back to top)
```

---

## Example API Responses

### Response with Follow-Up (Incomplete Stage)

```json
{
  "next_question": "That's a great start! Can you tell me more about how magic works? Is it common or rare? What's the cost of using it?",
  "is_complete": false,
  "current_stage": "world_identity",
  "gathered_so_far": {
    "locations": [],
    "facts": [
      {
        "content": "Fantasy world with magic",
        "fact_category": "current_state",
        "what_type": "general"
      }
    ]
  },
  "progress_percentage": 15
}
```

### Response Advancing to Next Stage

```json
{
  "next_question": "Excellent world concept! Now tell me about the key locations in your world. Describe 3-5 important places with their spatial relationships.",
  "is_complete": false,
  "current_stage": "locations",
  "gathered_so_far": {
    "locations": [],
    "facts": [
      {
        "content": "High fantasy world with unstable ancient magic",
        "fact_category": "current_state"
      },
      {
        "content": "World consists of floating sky islands",
        "fact_category": "geographic"
      },
      {
        "content": "Magic is rare and corrupting",
        "fact_category": "world_rule"
      }
    ]
  },
  "progress_percentage": 50
}
```

### Response Completing Wizard

```json
{
  "next_question": null,
  "is_complete": true,
  "current_stage": "complete",
  "gathered_so_far": {
    "locations": [
      {
        "name": "Skyreach",
        "description": "Capital city at the center",
        "location_type": "city",
        "relative_position": "center of the islands"
      },
      {
        "name": "Frostpeak",
        "description": "Frozen mountain in the far north",
        "location_type": "mountain",
        "relative_position": "far north"
      },
      {
        "name": "Verdant Forest",
        "description": "Lush jungle to the south",
        "location_type": "forest",
        "relative_position": "south of Skyreach"
      },
      {
        "name": "Ironhold",
        "description": "Mining colony",
        "location_type": "village",
        "relative_position": "between Skyreach and Frostpeak"
      }
    ],
    "facts": [ /* ... */ ]
  },
  "progress_percentage": 100
}
```

---

## Testing the Intelligent Wizard

### Test Case 1: Vague User

```bash
# Start wizard
curl -X POST http://localhost:5000/world-building/wizard/start \
  -H "Content-Type: application/json" \
  -d '{"world_id": 1}'

# Give vague response
curl -X POST http://localhost:5000/world-building/wizard/respond \
  -H "Content-Type: application/json" \
  -d '{"session_id": 1, "response": "A world with magic"}'

# Expected: Follow-up asking for magic details
# Actual response should include targeted question about magic system
```

### Test Case 2: Detailed User

```bash
# Give detailed response
curl -X POST http://localhost:5000/world-building/wizard/respond \
  -H "Content-Type: application/json" \
  -d '{"session_id": 1, "response": "High fantasy world with floating sky islands separated by toxic mist. Ancient magic is unstable and corrupts those who use it, capable of reality-warping effects."}'

# Expected: Accepts response, moves to locations stage
# Check: is_complete should be false, current_stage should still be world_identity or advance to locations
```

### Test Case 3: Insufficient Locations

```bash
# Give vague locations
curl -X POST http://localhost:5000/world-building/wizard/respond \
  -H "Content-Type: application/json" \
  -d '{"session_id": 1, "response": "A city, a forest, and a mountain"}'

# Expected: Follow-up asking for names and spatial relationships
# Check: next_question should probe for specifics
```

---

## Conclusion

The wizard now **intelligently detects vague responses** and asks targeted follow-up questions to gather sufficient detail for world creation. This ensures high-quality worlds while maintaining a natural conversational flow.

**Key Features:**
- ✅ LLM-driven completion evaluation
- ✅ Intelligent follow-up question generation
- ✅ Vagueness detection with specific examples
- ✅ Quality control for world consistency
- ✅ Fallback to simple logic if LLM fails
- ✅ Natural conversation flow with context awareness
