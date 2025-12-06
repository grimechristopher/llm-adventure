"""
World Building Requirements Configuration

This module defines the checklist of required information for world creation.
Developers can easily add, remove, or modify requirements here.

The wizard uses this checklist to:
1. Determine what questions to ask
2. Evaluate if enough information has been gathered
3. Identify gaps in the user's responses
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class FactRequirement(BaseModel):
    """
    A single required fact type for world building.
    """
    fact_type: str = Field(description="Type of fact (e.g., 'magic_system', 'technology_level')")
    fact_category: str = Field(description="Category: observed, historical, current_state, world_rule, etc.")
    what_type: Optional[str] = Field(default=None, description="What the fact is about: demographic, structural, etc.")
    min_count: int = Field(default=1, description="Minimum number of facts of this type required")
    display_name: str = Field(description="Human-readable name for this requirement")
    description: str = Field(description="What this requirement covers")
    example_good: str = Field(description="Example of a good fact that satisfies this")
    example_bad: str = Field(description="Example of a vague fact that doesn't satisfy this")
    prompt_hint: str = Field(description="Hint for LLM to ask about this if missing")


class LocationRequirement(BaseModel):
    """
    Requirements for locations in the world.
    """
    min_locations: int = Field(default=3, description="Minimum number of locations required")
    require_names: bool = Field(default=True, description="All locations must have names")
    require_spatial_relationships: bool = Field(default=True, description="Locations must have relative positions")
    require_variety: bool = Field(default=True, description="Locations should be different types (city, forest, etc.)")
    display_name: str = Field(default="Locations")
    description: str = Field(default="Key places that players can visit or reference")
    example_good: str = Field(default="Skyreach capital at center, Frostpeak far north, Verdant Forest south")
    example_bad: str = Field(default="a city, a forest, a mountain")
    prompt_hint: str = Field(default="Ask for named locations with spatial relationships")


class WorldBuildingChecklist:
    """
    Master checklist of requirements for world creation.

    Developers can modify this class to add/remove requirements.
    """

    # Location requirements
    LOCATION_REQUIREMENTS = LocationRequirement(
        min_locations=3,
        require_names=True,
        require_spatial_relationships=True,
        require_variety=True,
        display_name="Locations",
        description="Key places in the world with names and spatial relationships",
        example_good="Skyreach (capital, center), Frostpeak (mountain, far north), Verdant (forest, south)",
        example_bad="a city somewhere, a forest, some mountains",
        prompt_hint="Ask: What are the key locations? Where are they relative to each other?"
    )

    # Fact requirements
    FACT_REQUIREMENTS: List[FactRequirement] = [

        # 1. WORLD SETTING - What kind of world is this?
        FactRequirement(
            fact_type="world_setting",
            fact_category="current_state",
            what_type="geographic",
            min_count=2,
            display_name="World Setting",
            description="The physical nature and genre of the world",
            example_good="Floating sky islands separated by toxic mist below",
            example_bad="A fantasy world",
            prompt_hint="Ask about the physical world: Is it a planet? Floating islands? Underground? What makes the geography unique?"
        ),

        # 2. MAGIC SYSTEM (if applicable)
        FactRequirement(
            fact_type="magic_system",
            fact_category="world_rule",
            what_type="cultural",
            min_count=2,
            display_name="Magic System",
            description="How magic works, if it exists (or why it doesn't)",
            example_good="Magic is rare and corrupts users. It can warp reality but costs humanity.",
            example_bad="Magic exists",
            prompt_hint="Ask: How does magic work? Is it common or rare? What's the cost? If no magic, why not?"
        ),

        # 3. TECHNOLOGY LEVEL
        FactRequirement(
            fact_type="technology_level",
            fact_category="current_state",
            what_type="structural",
            min_count=1,
            display_name="Technology Level",
            description="What technology exists and how advanced it is",
            example_good="Medieval technology with primitive airships powered by magic crystals",
            example_bad="Medieval tech",
            prompt_hint="Ask: What's the technology level? Medieval? Steam-punk? High-tech? Any unique technologies?"
        ),

        # 4. MAJOR CONFLICT/TENSION
        FactRequirement(
            fact_type="major_conflict",
            fact_category="current_state",
            what_type="political",
            min_count=1,
            display_name="Major Conflict",
            description="The key tension, conflict, or problem in the world",
            example_good="Sky islands are slowly falling as ancient magic destabilizes. Nations fight over dwindling safe zones.",
            example_bad="There's some conflict",
            prompt_hint="Ask: What's the major conflict or tension? What are the key problems facing this world?"
        ),

        # 5. HISTORICAL CONTEXT (optional but valuable)
        FactRequirement(
            fact_type="history",
            fact_category="historical",
            what_type="cultural",
            min_count=1,
            display_name="Historical Context",
            description="Key events from the world's past that shape the present",
            example_good="Ancient civilization collapsed 500 years ago when they lost control of reality-warping magic",
            example_bad="Something happened long ago",
            prompt_hint="Ask: What's an important historical event that shaped this world?"
        ),

        # 6. CULTURAL ELEMENTS (optional)
        FactRequirement(
            fact_type="culture",
            fact_category="current_state",
            what_type="social",
            min_count=1,
            display_name="Cultural Elements",
            description="Social structures, customs, or beliefs that define societies",
            example_good="Sky-dwellers view ground as cursed. Social status determined by island elevation.",
            example_bad="Some cultures exist",
            prompt_hint="Ask: What are the key cultural elements? How do societies function?"
        ),
    ]

    @classmethod
    def get_all_requirements(cls) -> Dict[str, List[FactRequirement]]:
        """
        Get all requirements organized by category.

        Returns:
            Dictionary mapping category names to lists of requirements
        """
        return {
            "locations": [cls.LOCATION_REQUIREMENTS],
            "facts": cls.FACT_REQUIREMENTS
        }

    @classmethod
    def get_required_fact_types(cls) -> List[str]:
        """
        Get list of all required fact types.

        Returns:
            List of fact_type strings
        """
        return [req.fact_type for req in cls.FACT_REQUIREMENTS]

    @classmethod
    def get_requirement_by_type(cls, fact_type: str) -> Optional[FactRequirement]:
        """
        Get a specific requirement by fact type.

        Args:
            fact_type: Type of fact to look up

        Returns:
            FactRequirement or None if not found
        """
        for req in cls.FACT_REQUIREMENTS:
            if req.fact_type == fact_type:
                return req
        return None

    @classmethod
    def get_minimum_requirements(cls) -> Dict[str, int]:
        """
        Get minimum counts for each requirement.

        Returns:
            Dictionary mapping fact_type to min_count
        """
        return {
            req.fact_type: req.min_count
            for req in cls.FACT_REQUIREMENTS
        }

    @classmethod
    def generate_checklist_summary(cls) -> str:
        """
        Generate human-readable checklist summary for LLM prompts.

        Returns:
            Formatted string describing all requirements
        """
        lines = ["WORLD BUILDING REQUIREMENTS CHECKLIST:\n"]

        # Location requirements
        loc_req = cls.LOCATION_REQUIREMENTS
        lines.append(f"✓ {loc_req.display_name}: {loc_req.description}")
        lines.append(f"  Minimum: {loc_req.min_locations} locations")
        lines.append(f"  ✅ Good: {loc_req.example_good}")
        lines.append(f"  ❌ Bad: {loc_req.example_bad}\n")

        # Fact requirements
        for req in cls.FACT_REQUIREMENTS:
            lines.append(f"✓ {req.display_name}: {req.description}")
            lines.append(f"  Minimum: {req.min_count} fact(s)")
            lines.append(f"  ✅ Good: {req.example_good}")
            lines.append(f"  ❌ Bad: {req.example_bad}\n")

        return "\n".join(lines)


# ========== CUSTOMIZATION EXAMPLES ==========

# Example: Add a new requirement for ECONOMY
# Simply add to FACT_REQUIREMENTS list:
"""
FactRequirement(
    fact_type="economy",
    fact_category="current_state",
    what_type="economic",
    min_count=1,
    display_name="Economic System",
    description="How trade, currency, and resources work",
    example_good="Trade between islands via airship. Crystal shards used as currency.",
    example_bad="They trade stuff",
    prompt_hint="Ask: How does the economy work? What do people trade? Is there currency?"
)
"""

# Example: Remove a requirement
# Simply delete or comment out the requirement from FACT_REQUIREMENTS

# Example: Adjust minimum counts
# Change min_count in the FactRequirement:
"""
FactRequirement(
    ...
    min_count=3,  # Changed from 1 to 3
    ...
)
"""

# Example: Make a requirement optional
# Set min_count to 0:
"""
FactRequirement(
    ...
    min_count=0,  # Now optional
    ...
)
"""
