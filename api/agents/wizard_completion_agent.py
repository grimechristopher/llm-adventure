"""
DeepAgent for wizard stage completion evaluation.

Replaces simple LLM prompt with extended reasoning about world quality.
Uses structured output via Pydantic for reliable parsing.
"""

from deepagents import create_deep_agent
from langchain_core.output_parsers import PydanticOutputParser
from tools import WORLD_BUILDING_TOOLS
from models.world_building import CompletionEvaluation

# Create parser for structured output
completion_parser = PydanticOutputParser(pydantic_object=CompletionEvaluation)

WIZARD_COMPLETION_SYSTEM_PROMPT = """You are a world-building quality evaluator.

Your task: Determine if the user has provided sufficient, specific detail to create an engaging fantasy world.

EVALUATION CRITERIA:
1. Specificity: Vague responses like "magic exists" are insufficient. Need details like "magic corrupts users, rare, warps reality"
2. Completeness: Check all requirements satisfied (world setting, magic system, technology, conflict, history, culture, locations)
3. Coherence: Facts should be internally consistent, not contradictory
4. Richness: Enough detail to build a playable world

AVAILABLE TOOLS:
- query_world_facts: See what facts have been gathered
- query_world_locations: See what locations exist
- validate_fact_consistency: Check for contradictions

PROCESS:
1. Use tools to retrieve gathered data
2. Evaluate each requirement category
3. Identify gaps or vague responses
4. Calculate quality score (0.0 = no useful data, 1.0 = exceptional detail)
5. Return structured decision

OUTPUT FORMAT:
{format_instructions}

IMPORTANT: You MUST return valid JSON matching the schema above. Include:
- is_complete: boolean (true only if quality_score >= 0.8 and no critical gaps)
- reasoning: detailed step-by-step analysis
- missing_elements: list of specific gaps (e.g., "no magic system details", "only 1 location provided")
- vague_responses_detected: list of examples (e.g., "user said 'some magic' without specifics")
- quality_score: float 0.0-1.0 based on specificity and completeness
- next_question_suggestion: specific question to fill the biggest gap (if not complete)
""".replace("{format_instructions}", completion_parser.get_format_instructions())

def create_wizard_completion_agent():
    """
    Create DeepAgent for wizard stage completion evaluation.

    Returns an agent that uses tools to analyze gathered world data
    and returns structured CompletionEvaluation output.
    """
    return create_deep_agent(
        tools=WORLD_BUILDING_TOOLS,
        system_prompt=WIZARD_COMPLETION_SYSTEM_PROMPT,
        model=None  # Use default Claude Sonnet 4.5
    )
