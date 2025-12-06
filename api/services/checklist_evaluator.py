"""
Checklist Evaluator Service

This service evaluates gathered world-building data against the configurable
requirements checklist to determine:
1. What requirements are satisfied
2. What's still missing
3. How complete the world-building is
"""

from typing import Dict, List, Tuple
from config.world_requirements import WorldBuildingChecklist, FactRequirement
from utils.logging import get_logger

logger = get_logger(__name__)


class ChecklistItem:
    """Represents a single checklist item with completion status"""

    def __init__(self, requirement: FactRequirement):
        self.requirement = requirement
        self.gathered_count = 0
        self.is_satisfied = False
        self.gathered_examples: List[str] = []

    @property
    def progress_percentage(self) -> int:
        """Calculate completion percentage for this item"""
        if self.requirement.min_count == 0:
            return 100  # Optional items are always "complete"
        percentage = int((self.gathered_count / self.requirement.min_count) * 100)
        return min(100, percentage)

    def __repr__(self):
        status = "✅" if self.is_satisfied else "❌"
        return f"{status} {self.requirement.display_name}: {self.gathered_count}/{self.requirement.min_count}"


class ChecklistEvaluator:
    """
    Evaluates gathered world-building data against requirements checklist.
    """

    def __init__(self):
        self.checklist = WorldBuildingChecklist()

    def evaluate_gathered_data(self, gathered_data: Dict) -> Dict:
        """
        Evaluate gathered data against requirements checklist.

        Args:
            gathered_data: Dictionary with 'locations' and 'facts' lists

        Returns:
            Dictionary with evaluation results:
            {
                "overall_complete": bool,
                "overall_percentage": int,
                "satisfied_requirements": List[str],
                "missing_requirements": List[Dict],
                "location_evaluation": Dict,
                "fact_evaluations": List[ChecklistItem],
                "next_priority": str  # What to ask about next
            }
        """
        logger.info("Evaluating gathered data against checklist")

        # Evaluate locations
        location_eval = self._evaluate_locations(gathered_data.get('locations', []))

        # Evaluate facts
        fact_items = self._evaluate_facts(gathered_data.get('facts', []))

        # Calculate overall status
        all_items = [location_eval['checklist_item']] + fact_items
        satisfied = [item for item in all_items if item.is_satisfied]
        missing = [item for item in all_items if not item.is_satisfied]

        overall_complete = len(missing) == 0
        overall_percentage = self._calculate_overall_percentage(all_items)

        # Determine next priority (what to ask about)
        next_priority = self._determine_next_priority(missing)

        result = {
            "overall_complete": overall_complete,
            "overall_percentage": overall_percentage,
            "satisfied_requirements": [item.requirement.display_name for item in satisfied],
            "missing_requirements": [
                {
                    "name": item.requirement.display_name,
                    "description": item.requirement.description,
                    "current": item.gathered_count,
                    "required": item.requirement.min_count,
                    "prompt_hint": item.requirement.prompt_hint,
                    "example_good": item.requirement.example_good,
                    "example_bad": item.requirement.example_bad
                }
                for item in missing
            ],
            "location_evaluation": location_eval,
            "fact_evaluations": [
                {
                    "name": item.requirement.display_name,
                    "satisfied": item.is_satisfied,
                    "count": item.gathered_count,
                    "required": item.requirement.min_count,
                    "progress": item.progress_percentage,
                    "examples": item.gathered_examples
                }
                for item in fact_items
            ],
            "next_priority": next_priority
        }

        logger.info("Checklist evaluation complete",
                    overall_complete=overall_complete,
                    percentage=overall_percentage,
                    satisfied=len(satisfied),
                    missing=len(missing))

        return result

    def _evaluate_locations(self, locations: List[Dict]) -> Dict:
        """
        Evaluate locations against requirements.

        Args:
            locations: List of location dictionaries

        Returns:
            Dictionary with location evaluation details
        """
        loc_req = self.checklist.LOCATION_REQUIREMENTS
        item = ChecklistItem(FactRequirement(
            fact_type="locations",
            fact_category="observed",
            min_count=loc_req.min_locations,
            display_name=loc_req.display_name,
            description=loc_req.description,
            example_good=loc_req.example_good,
            example_bad=loc_req.example_bad,
            prompt_hint=loc_req.prompt_hint
        ))

        item.gathered_count = len(locations)

        # Check quality requirements
        issues = []

        if loc_req.require_names:
            unnamed = [loc for loc in locations if not loc.get('name') or not loc['name'].strip()]
            if unnamed:
                issues.append(f"{len(unnamed)} location(s) missing names")

        if loc_req.require_spatial_relationships:
            no_position = [loc for loc in locations if not loc.get('relative_position')]
            if no_position:
                issues.append(f"{len(no_position)} location(s) missing spatial relationships")

        if loc_req.require_variety:
            types = set(loc.get('location_type') for loc in locations if loc.get('location_type'))
            if len(types) < 2 and len(locations) >= 3:
                issues.append("Need more variety in location types")

        # Item is satisfied if count met and no quality issues
        item.is_satisfied = item.gathered_count >= loc_req.min_locations and len(issues) == 0

        # Gather examples
        item.gathered_examples = [
            f"{loc.get('name', 'Unnamed')} ({loc.get('location_type', 'unknown')}): {loc.get('relative_position', 'no position')}"
            for loc in locations[:3]  # First 3 examples
        ]

        return {
            "checklist_item": item,
            "count": len(locations),
            "required": loc_req.min_locations,
            "has_names": loc_req.require_names and len(issues) == 0,
            "has_spatial_relationships": loc_req.require_spatial_relationships and len(issues) == 0,
            "has_variety": loc_req.require_variety and len(issues) == 0,
            "issues": issues
        }

    def _evaluate_facts(self, facts: List[Dict]) -> List[ChecklistItem]:
        """
        Evaluate facts against requirements.

        Args:
            facts: List of fact dictionaries

        Returns:
            List of ChecklistItem objects for each requirement
        """
        items = []

        for req in self.checklist.FACT_REQUIREMENTS:
            item = ChecklistItem(req)

            # Count matching facts
            # Match by fact_type if available, otherwise try to infer from what_type or content
            matching_facts = self._find_matching_facts(facts, req)
            item.gathered_count = len(matching_facts)
            item.is_satisfied = item.gathered_count >= req.min_count

            # Gather examples
            item.gathered_examples = [
                fact.get('content', '')[:100] + ('...' if len(fact.get('content', '')) > 100 else '')
                for fact in matching_facts[:3]
            ]

            items.append(item)

        return items

    def _find_matching_facts(self, facts: List[Dict], requirement: FactRequirement) -> List[Dict]:
        """
        Find facts that match a requirement.

        Args:
            facts: List of fact dictionaries
            requirement: Requirement to match against

        Returns:
            List of matching facts
        """
        matching = []

        for fact in facts:
            # Primary match: fact_type (if fact has it)
            if 'fact_type' in fact and fact['fact_type'] == requirement.fact_type:
                matching.append(fact)
                continue

            # Secondary match: category and what_type
            category_match = fact.get('fact_category') == requirement.fact_category
            type_match = (
                requirement.what_type is None or
                fact.get('what_type') == requirement.what_type
            )

            # Fallback: keyword matching in content (less reliable)
            content = fact.get('content', '').lower()
            keyword_match = self._keyword_match(content, requirement.fact_type)

            if category_match and type_match and keyword_match:
                matching.append(fact)

        return matching

    def _keyword_match(self, content: str, fact_type: str) -> bool:
        """
        Check if content contains keywords related to fact type.

        Args:
            content: Fact content
            fact_type: Type to check for

        Returns:
            True if keywords found
        """
        keyword_map = {
            "world_setting": ["world", "planet", "setting", "geography", "islands", "continents", "realm"],
            "magic_system": ["magic", "magical", "spell", "mana", "arcane", "enchant"],
            "technology_level": ["technology", "tech", "medieval", "steam", "industrial", "advanced", "airship"],
            "major_conflict": ["conflict", "war", "tension", "problem", "crisis", "struggle", "falling", "destabilize", "fight", "battle"],
            "history": ["ancient", "ago", "history", "past", "historical", "founded", "collapsed"],
            "culture": ["culture", "society", "custom", "tradition", "belief", "social", "view", "dweller"],
        }

        keywords = keyword_map.get(fact_type, [])
        return any(keyword in content for keyword in keywords)

    def _calculate_overall_percentage(self, items: List[ChecklistItem]) -> int:
        """
        Calculate overall completion percentage.

        Args:
            items: List of checklist items

        Returns:
            Percentage complete (0-100)
        """
        if not items:
            return 0

        total_progress = sum(item.progress_percentage for item in items)
        return int(total_progress / len(items))

    def _determine_next_priority(self, missing: List[ChecklistItem]) -> str:
        """
        Determine what to ask about next based on missing requirements.

        Args:
            missing: List of unsatisfied checklist items

        Returns:
            Prompt hint for next question
        """
        if not missing:
            return "All requirements satisfied"

        # Prioritize by requirement order (first in list = highest priority)
        # This matches the order in WorldBuildingChecklist.FACT_REQUIREMENTS
        return missing[0].requirement.prompt_hint

    def generate_progress_report(self, gathered_data: Dict) -> str:
        """
        Generate human-readable progress report.

        Args:
            gathered_data: Dictionary with locations and facts

        Returns:
            Formatted progress report string
        """
        evaluation = self.evaluate_gathered_data(gathered_data)

        lines = [
            f"\n{'='*60}",
            f"WORLD BUILDING PROGRESS: {evaluation['overall_percentage']}%",
            f"{'='*60}\n"
        ]

        # Satisfied requirements
        if evaluation['satisfied_requirements']:
            lines.append("✅ SATISFIED REQUIREMENTS:")
            for req_name in evaluation['satisfied_requirements']:
                lines.append(f"   • {req_name}")
            lines.append("")

        # Missing requirements
        if evaluation['missing_requirements']:
            lines.append("❌ MISSING REQUIREMENTS:")
            for missing in evaluation['missing_requirements']:
                lines.append(f"   • {missing['name']}: {missing['current']}/{missing['required']}")
                lines.append(f"     Hint: {missing['prompt_hint']}")
            lines.append("")

        # Next priority
        lines.append(f"🎯 NEXT PRIORITY: {evaluation['next_priority']}\n")

        return "\n".join(lines)
