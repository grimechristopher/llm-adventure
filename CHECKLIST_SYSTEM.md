```markdown
# Configurable Checklist System

## Overview

The wizard now uses a **configurable checklist** to ensure all required information is gathered before world creation. Developers can easily add, remove, or modify requirements without touching the core wizard logic.

## Key Features

✅ **Configurable Requirements** - Add/remove fact types in one central file
✅ **Automatic Checking** - Evaluates checklist after every user response
✅ **Intelligent Targeting** - LLM asks about missing requirements
✅ **Quality Control** - Rejects vague responses using examples
✅ **Progress Tracking** - Shows completion percentage per requirement

---

## How It Works

### 1. Configuration File

**Location:** `api/config/world_requirements.py`

This file defines ALL requirements for world building:

```python
FACT_REQUIREMENTS: List[FactRequirement] = [
    FactRequirement(
        fact_type="magic_system",
        fact_category="world_rule",
        min_count=2,
        display_name="Magic System",
        description="How magic works, if it exists",
        example_good="Magic is rare and corrupts users. Can warp reality.",
        example_bad="Magic exists",
        prompt_hint="Ask: How does magic work? Common or rare? Cost?"
    ),
    # ... more requirements
]
```

### 2. Checklist Evaluator

**Location:** `api/services/checklist_evaluator.py`

Evaluates gathered data against requirements:

```python
evaluator = ChecklistEvaluator()
result = evaluator.evaluate_gathered_data(gathered_data)

# Returns:
{
    "overall_complete": False,
    "overall_percentage": 65,
    "satisfied_requirements": ["Locations", "World Setting"],
    "missing_requirements": [
        {
            "name": "Magic System",
            "description": "How magic works...",
            "current": 0,
            "required": 2,
            "prompt_hint": "Ask: How does magic work?",
            "example_good": "Magic is rare and corrupts...",
            "example_bad": "Magic exists"
        }
    ],
    "next_priority": "Ask: How does magic work? Common or rare?"
}
```

### 3. Integration with Wizard

**Location:** `api/services/world_building_service.py`

The wizard automatically:

1. **After each user response** - Runs checklist evaluation
2. **Checks completion** - Uses checklist to determine if stage complete
3. **Generates questions** - Uses checklist hints for targeted follow-ups
4. **Tracks progress** - Shows user completion percentage

---

## Default Requirements

### Locations (3 minimum)

- **Require Names**: ✅ Yes
- **Require Spatial Relationships**: ✅ Yes
- **Require Variety**: ✅ Yes (different types)

**Good Example:**
```
Skyreach (capital, center)
Frostpeak (mountain, far north)
Verdant Forest (south of Skyreach)
```

**Bad Example:**
```
a city, a forest, a mountain
```

### Facts

#### 1. World Setting (2 minimum)
- **Category:** current_state
- **What Type:** geographic

**Good:** "Floating sky islands separated by toxic mist below"
**Bad:** "A fantasy world"

#### 2. Magic System (2 minimum)
- **Category:** world_rule
- **What Type:** cultural

**Good:** "Magic is rare and corrupts users. Can warp reality but costs humanity."
**Bad:** "Magic exists"

#### 3. Technology Level (1 minimum)
- **Category:** current_state
- **What Type:** structural

**Good:** "Medieval tech with primitive airships powered by magic crystals"
**Bad:** "Medieval tech"

#### 4. Major Conflict (1 minimum)
- **Category:** current_state
- **What Type:** political

**Good:** "Sky islands slowly falling as ancient magic destabilizes. Nations fight over safe zones."
**Bad:** "There's some conflict"

#### 5. Historical Context (1 minimum)
- **Category:** historical
- **What Type:** cultural

**Good:** "Ancient civilization collapsed 500 years ago when they lost control of reality-warping magic"
**Bad:** "Something happened long ago"

#### 6. Cultural Elements (1 minimum)
- **Category:** current_state
- **What Type:** social

**Good:** "Sky-dwellers view ground as cursed. Status determined by island elevation."
**Bad:** "Some cultures exist"

---

## Customizing Requirements

### Adding a New Requirement

**File:** `api/config/world_requirements.py`

Add to `FACT_REQUIREMENTS` list:

```python
FactRequirement(
    fact_type="economy",  # Unique identifier
    fact_category="current_state",  # observed, historical, current_state, etc.
    what_type="economic",  # demographic, structural, political, etc.
    min_count=2,  # Minimum number required
    display_name="Economic System",  # User-friendly name
    description="How trade, currency, and resources work",
    example_good="Trade between islands via airship. Crystal shards currency.",
    example_bad="They trade stuff",
    prompt_hint="Ask: How does the economy work? What do people trade?"
)
```

**That's it!** The wizard will automatically:
- Check for this requirement after each response
- Ask about it if missing
- Show progress toward completing it

### Removing a Requirement

**Option 1: Delete it**
```python
# Just delete or comment out the FactRequirement
```

**Option 2: Make it optional**
```python
FactRequirement(
    ...
    min_count=0,  # Set to 0 = optional
    ...
)
```

### Adjusting Minimum Counts

```python
FactRequirement(
    fact_type="magic_system",
    min_count=3,  # Changed from 2 to 3
    ...
)
```

### Changing Location Requirements

```python
LOCATION_REQUIREMENTS = LocationRequirement(
    min_locations=5,  # Changed from 3 to 5
    require_names=True,
    require_spatial_relationships=False,  # Make spatial optional
    require_variety=True
)
```

---

## Example Wizard Flow with Checklist

### Turn 1: Vague Response

**User:** "A fantasy world"

**System:**
```json
{
  "checklist": {
    "overall_percentage": 5,
    "satisfied": [],
    "missing": [
      "World Setting (0/2)",
      "Magic System (0/2)",
      "Technology Level (0/1)",
      "Major Conflict (0/1)",
      "Historical Context (0/1)",
      "Cultural Elements (0/1)",
      "Locations (0/3)"
    ],
    "next_priority": "Ask about physical world and geography"
  }
}
```

**Wizard:** "That's a great start! Can you tell me more about the physical world? Is it a planet? Floating islands? Underground? What makes the geography unique?"

---

### Turn 2: Better Response

**User:** "Floating sky islands separated by toxic mist below. Ancient magic is unstable and corrupts users."

**System:**
```json
{
  "checklist": {
    "overall_percentage": 35,
    "satisfied": ["World Setting (2/2)"],
    "missing": [
      "Magic System (1/2)",  // Partial!
      "Technology Level (0/1)",
      "Major Conflict (0/1)",
      "Historical Context (0/1)",
      "Cultural Elements (0/1)",
      "Locations (0/3)"
    ],
    "next_priority": "Ask: How does magic work? Cost?"
  }
}
```

**Wizard:** "Fascinating! You mentioned magic is unstable and corrupting. Can you tell me more about how it works? What can magic users do? What's the cost of using it?"

---

### Turn 3: Complete Magic System

**User:** "Magic can warp reality but gradually erodes the user's humanity. Very few dare use it anymore."

**System:**
```json
{
  "checklist": {
    "overall_percentage": 50,
    "satisfied": [
      "World Setting (2/2)",
      "Magic System (2/2)"  // Complete!
    ],
    "missing": [
      "Technology Level (0/1)",
      "Major Conflict (0/1)",
      "Historical Context (0/1)",
      "Cultural Elements (0/1)",
      "Locations (0/3)"
    ],
    "next_priority": "Ask about technology level"
  }
}
```

**Wizard:** "Excellent! Now tell me about the technology level. Is this medieval? Steam-punk? Any unique technologies?"

---

### Completion Check

After each response, the system:

1. **Extracts facts and locations**
2. **Runs checklist evaluation**
3. **Checks if all requirements satisfied**
4. **If incomplete** → Asks targeted question about next priority
5. **If complete** → Advances to next stage or finalizes

---

## Checklist Evaluation API

### Check Progress

```python
from services.checklist_evaluator import ChecklistEvaluator

evaluator = ChecklistEvaluator()
result = evaluator.evaluate_gathered_data({
    'locations': [...],
    'facts': [...]
})

print(result['overall_percentage'])  # 0-100
print(result['missing_requirements'])  # What's missing
print(result['next_priority'])  # What to ask next
```

### Generate Progress Report

```python
report = evaluator.generate_progress_report(gathered_data)
print(report)
```

**Output:**
```
============================================================
WORLD BUILDING PROGRESS: 65%
============================================================

✅ SATISFIED REQUIREMENTS:
   • World Setting
   • Magic System
   • Locations

❌ MISSING REQUIREMENTS:
   • Technology Level: 0/1
     Hint: Ask: What's the technology level?
   • Major Conflict: 0/1
     Hint: Ask: What's the major conflict?

🎯 NEXT PRIORITY: Ask: What's the technology level?
```

---

## Advanced Customization

### Custom Fact Matching

By default, facts are matched by keywords. You can customize this:

**File:** `api/services/checklist_evaluator.py`

```python
def _keyword_match(self, content: str, fact_type: str) -> bool:
    keyword_map = {
        "economy": ["trade", "currency", "money", "goods", "merchant"],
        "religion": ["god", "deity", "worship", "prayer", "faith"],
        # Add custom mappings
    }
    keywords = keyword_map.get(fact_type, [])
    return any(keyword in content for keyword in keywords)
```

### Dynamic Requirements

Requirements can be conditional:

```python
# In WizardOrchestrationService
def get_requirements_for_world(self, world_genre):
    """Return different requirements based on world type"""
    if world_genre == "sci-fi":
        return SciFiRequirements()
    elif world_genre == "fantasy":
        return FantasyRequirements()
    else:
        return DefaultRequirements()
```

### Requirement Dependencies

Some requirements could depend on others:

```python
FactRequirement(
    fact_type="magic_schools",
    depends_on="magic_system",  # Only check if magic_system satisfied
    min_count=1,
    ...
)
```

---

## Testing the Checklist

### Unit Test

```python
def test_checklist_evaluation():
    evaluator = ChecklistEvaluator()

    # Minimal data - should be incomplete
    result = evaluator.evaluate_gathered_data({
        'locations': [],
        'facts': [{'content': 'A fantasy world', 'fact_category': 'current_state'}]
    })

    assert result['overall_complete'] == False
    assert result['overall_percentage'] < 20
    assert 'Magic System' in [m['name'] for m in result['missing_requirements']]

    # Complete data - should be complete
    result = evaluator.evaluate_gathered_data({
        'locations': [
            {'name': 'Skyreach', 'relative_position': 'center'},
            {'name': 'Frostpeak', 'relative_position': 'far north'},
            {'name': 'Verdant', 'relative_position': 'south'}
        ],
        'facts': [
            {'content': 'Floating sky islands', 'fact_category': 'current_state', 'what_type': 'geographic'},
            {'content': 'Toxic mist below', 'fact_category': 'current_state', 'what_type': 'geographic'},
            {'content': 'Magic is rare', 'fact_category': 'world_rule'},
            {'content': 'Magic corrupts users', 'fact_category': 'world_rule'},
            # ... all required facts
        ]
    })

    assert result['overall_complete'] == True
    assert result['overall_percentage'] == 100
```

### Integration Test

```bash
# Test wizard with checklist
curl -X POST http://localhost:5000/world-building/wizard/start \
  -H "Content-Type: application/json" \
  -d '{"world_id": 1}'

# Give incomplete response
curl -X POST http://localhost:5000/world-building/wizard/respond \
  -H "Content-Type: application/json" \
  -d '{"session_id": 1, "response": "A fantasy world"}'

# Check response includes missing requirements
# next_question should probe for specifics based on checklist
```

---

## Benefits

### 1. **Easy Customization**
- Add new requirements in minutes
- No need to modify wizard logic
- Changes apply immediately

### 2. **Quality Control**
- Rejects vague responses automatically
- Provides good/bad examples
- Ensures comprehensive world building

### 3. **Targeted Questions**
- Wizard knows exactly what's missing
- Asks specific questions to fill gaps
- No repetitive or irrelevant questions

### 4. **Progress Tracking**
- User sees completion percentage
- Clear indication of what's needed
- Motivation to provide detail

### 5. **Debugging Support**
- Checklist evaluations logged
- Can see exactly what's missing
- Easy to identify extraction issues

---

## Configuration Best Practices

### 1. Keep Requirements Focused
❌ **Bad:** "World details" (too broad)
✅ **Good:** "Magic System", "Technology Level" (specific)

### 2. Provide Clear Examples
❌ **Bad:** "Some description of magic"
✅ **Good:** "Magic is rare and corrupts users. Can warp reality but costs humanity."

### 3. Reasonable Minimums
❌ **Bad:** min_count=10 (too many)
✅ **Good:** min_count=1-3 (achievable)

### 4. Useful Prompt Hints
❌ **Bad:** "Tell me about magic"
✅ **Good:** "Ask: How does magic work? Is it common or rare? What's the cost?"

### 5. Match Categories Correctly
- **world_rule**: How things work (magic system, physics)
- **current_state**: How things are now (conflicts, technology)
- **historical**: Past events
- **observed**: Direct observations
- **cultural**: Social/cultural elements

---

## Troubleshooting

### Requirement Not Being Detected

**Problem:** Facts created but checklist shows 0/X

**Solution:** Check keyword matching in `checklist_evaluator.py`

```python
# Add keywords for your fact_type
keyword_map = {
    "your_fact_type": ["keyword1", "keyword2", "keyword3"]
}
```

### LLM Not Asking About Requirement

**Problem:** Checklist shows missing but wizard doesn't ask

**Solution:** Check `prompt_hint` is clear and actionable

```python
prompt_hint="Ask: What's the [specific thing]? How does [it] work?"
```

### Progress Stuck at X%

**Problem:** User keeps answering but percentage doesn't increase

**Solution:**
1. Check if answers match fact_category and what_type
2. Verify keyword matching includes user's terminology
3. Check logs for extraction failures

---

## Future Enhancements

### Planned Features

1. **Conditional Requirements**
   - "If magic_system, then require magic_schools"
   - Different requirements for sci-fi vs fantasy

2. **Requirement Weights**
   - Some requirements more important than others
   - Weighted progress calculation

3. **User-Defined Requirements**
   - Users can specify custom requirements
   - "I want detailed economy and religion"

4. **Adaptive Minimums**
   - LLM can adjust min_count based on quality
   - 1 excellent fact > 3 vague facts

5. **Requirement Templates**
   - Pre-built sets for common genres
   - Fantasy template, Sci-fi template, etc.

---

## Summary

The checklist system provides:

✅ **Configurable** - One file controls all requirements
✅ **Automatic** - Checks after every response
✅ **Intelligent** - Guides LLM to ask targeted questions
✅ **Quality-Focused** - Rejects vague responses
✅ **Trackable** - Clear progress indication
✅ **Extensible** - Easy to add custom requirements

**Files:**
- `api/config/world_requirements.py` - Define requirements
- `api/services/checklist_evaluator.py` - Evaluation logic
- `api/services/world_building_service.py` - Integration with wizard

**To customize:** Just edit `world_requirements.py` and the wizard automatically adapts!
```
