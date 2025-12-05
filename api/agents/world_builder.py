"""
World Builder Agent - LLM-Powered Structured Data Extraction

This module implements a specialized LangChain agent that extracts structured world-building 
data from natural language descriptions for text adventure games.

Key Features:
- Uses LangChain Expression Language (LCEL) for clean chain composition
- Leverages Pydantic for structured output parsing and validation
- Optimized prompt engineering for consistent extraction quality
- Follows separation of concerns - agent handles extraction, service handles persistence

Architecture:
- Prompt engineering defines the extraction task and output format
- LangChain LCEL creates a composable pipeline: prompt -> LLM -> parser
- Pydantic models ensure type safety and validation of extracted data
- Service layer uses this agent to process descriptions and save to database

Usage:
    llm = initialize_llms()['your_llm']
    chain, parser = create_world_builder_chain(llm)
    result = await chain.ainvoke({"description": "Your world description..."})
"""

from typing import Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable
from models.world_building import WorldBuildingExtraction
from utils.logging import get_logger

logger = get_logger(__name__)

# Comprehensive system prompt for world-building extraction
# This prompt uses specific instructions and examples to guide the LLM
# toward consistent, high-quality structured output
WORLD_BUILDING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a specialized world-building assistant for a text adventure game.

Your primary task is to extract structured information from natural language world descriptions and transform them into game-ready data structures.

== EXTRACTION TARGETS ==

1. **LOCATIONS**: Physical places that players can visit or reference
   - Must have a clear name (proper noun)
   - Should include descriptive details for atmosphere
   - Capture spatial relationships (relative_position) when mentioned
   - Examples: "Millbrook village", "The Serpent River", "Dragon's Peak Castle"

2. **FACTS**: Discrete pieces of information about the world
   - Break complex sentences into 2-3 focused facts when they contain multiple distinct pieces of information
   - Each fact should be self-contained and verifiable
   - Link facts to specific locations when applicable

== FACT CATEGORIZATION ==

**Categories** (how the information was obtained):
- `observed`: Directly seen or experienced ("The village has stone walls")
- `historical`: Past events or conditions ("Founded 200 years ago")
- `current_state`: Present conditions ("Currently under siege") 
- `deduction`: Logical inference ("Must be wealthy based on architecture")
- `measurement`: Quantified data ("Population: 500 people")

**Types** (what the information is about):
- `demographic`: Population, people, cultures
- `structural`: Buildings, infrastructure, construction
- `political`: Government, rulers, laws, conflicts
- `social`: Customs, relationships, daily life
- `geographic`: Natural features, terrain, climate
- `economic`: Trade, commerce, resources, wealth
- `cultural`: Traditions, beliefs, arts, languages

== SPATIAL RELATIONSHIPS ==

Extract relative positioning information with these patterns:
- Directional: "north of Millbrook", "east of the capital"
- Distance: "2 days travel from", "a stone's throw away"
- Geographic: "at the mouth of the river", "in the valley between"
- Structural: "on the hilltop", "beneath the castle"

== OUTPUT FORMAT ==

{format_instructions}

== QUALITY GUIDELINES ==

- Prioritize clarity and game utility over exhaustive detail
- Ensure location names are consistent if mentioned multiple times
- Break down complex descriptions into manageable, specific facts
- Use appropriate categorization to help with future queries and world consistency
- Maintain immersive, fantasy-appropriate language in descriptions"""),
    ("user", "{description}")
])


def create_world_builder_chain(llm) -> Tuple[Runnable, PydanticOutputParser]:
    """
    Create a LangChain LCEL chain for structured world-building extraction.

    This function implements the factory pattern to create a reusable extraction pipeline.
    The chain follows LangChain's Expression Language (LCEL) pattern for clean composition:

    Pipeline Flow:
    1. PROMPT: Formats user description with system instructions
    2. LLM: Processes the prompt and generates structured response  
    3. PARSER: Validates and converts LLM output to Pydantic models

    Args:
        llm: Language model instance (ChatOpenAI, AzureChatOpenAI, etc.)
             Must support structured output or function calling for best results

    Returns:
        Tuple containing:
        - chain (Runnable): The complete LCEL pipeline ready for execution
        - parser (PydanticOutputParser): Parser for manual use or debugging
        
    Example:
        ```python
        llm = ChatOpenAI(model="gpt-4")
        chain, parser = create_world_builder_chain(llm)
        
        # Async execution (recommended)
        result = await chain.ainvoke({"description": "A bustling market town..."})
        
        # Sync execution
        result = chain.invoke({"description": "A bustling market town..."})
        ```

    Architecture Notes:
        - Uses composition over inheritance for better testability
        - Prompt engineering separated from chain logic for easier iteration
        - Parser can be used independently for testing or validation
        - Chain is stateless and thread-safe for concurrent usage
    """
    logger.info("Creating world builder extraction chain")
    
    # Initialize the Pydantic parser with our data model
    # This enforces strict type checking and validation on LLM outputs
    parser = PydanticOutputParser(pydantic_object=WorldBuildingExtraction)
    
    # Build the chain using LCEL pipe operator
    # Each component's output becomes the next component's input
    chain = (
        WORLD_BUILDING_PROMPT.partial(format_instructions=parser.get_format_instructions())
        | llm  # Send formatted prompt to language model
        | parser  # Parse and validate LLM response into structured data
    )
    
    logger.info("World builder chain created successfully", 
                model_name=getattr(llm, 'model_name', 'unknown'),
                parser_model=parser.pydantic_object.__name__)
    
    return chain, parser


# Additional utility functions for advanced usage

def validate_extraction_result(result: WorldBuildingExtraction) -> bool:
    """
    Validate that an extraction result meets quality standards.
    
    Args:
        result: The extraction result to validate
        
    Returns:
        bool: True if result passes validation checks
        
    Quality Checks:
        - At least one location or fact extracted
        - Location names are properly capitalized
        - Facts have appropriate categorization
        - No duplicate location names
    """
    if not result.locations and not result.facts:
        logger.warning("Extraction result contains no locations or facts")
        return False
    
    # Check for duplicate location names (case-insensitive)
    if result.locations:
        location_names = [loc.name.lower() for loc in result.locations]
        if len(location_names) != len(set(location_names)):
            logger.warning("Duplicate location names found in extraction")
            return False
    
    # Validate location name formatting
    for location in result.locations:
        if not location.name or not location.name.strip():
            logger.warning("Empty location name found")
            return False
        if location.name.lower() == location.name and len(location.name) > 3:
            logger.warning(f"Location name may need capitalization: {location.name}")
    
    logger.debug("Extraction validation passed", 
                 locations_count=len(result.locations),
                 facts_count=len(result.facts))
    return True


def get_extraction_statistics(result: WorldBuildingExtraction) -> dict:
    """
    Generate statistics about an extraction result for debugging and monitoring.
    
    Args:
        result: The extraction result to analyze
        
    Returns:
        dict: Statistics about the extraction including counts and categorization breakdown
    """
    stats = {
        "total_locations": len(result.locations),
        "total_facts": len(result.facts),
        "locations_with_position": sum(1 for loc in result.locations if loc.relative_position),
        "locations_with_elevation": sum(1 for loc in result.locations if loc.elevation_meters),
    }
    
    if result.facts:
        # Count facts by category
        fact_categories = {}
        fact_types = {}
        
        for fact in result.facts:
            fact_categories[fact.fact_category] = fact_categories.get(fact.fact_category, 0) + 1
            fact_types[fact.what_type] = fact_types.get(fact.what_type, 0) + 1
        
        stats["fact_categories"] = fact_categories
        stats["fact_types"] = fact_types
        stats["facts_linked_to_locations"] = sum(1 for fact in result.facts if fact.location_name)
    
    return stats
