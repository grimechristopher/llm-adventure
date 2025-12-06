#!/usr/bin/env python3
"""
Quick test script to verify checklist evaluation works correctly
"""
from services.checklist_evaluator import ChecklistEvaluator

def test_empty_data():
    """Test with no data - should be incomplete"""
    evaluator = ChecklistEvaluator()

    result = evaluator.evaluate_gathered_data({
        'locations': [],
        'facts': []
    })

    print("=" * 60)
    print("TEST 1: Empty Data")
    print("=" * 60)
    print(f"Overall complete: {result['overall_complete']}")
    print(f"Overall percentage: {result['overall_percentage']}%")
    print(f"Satisfied: {result['satisfied_requirements']}")
    print(f"Missing: {len(result['missing_requirements'])} requirements")
    print(f"Next priority: {result['next_priority']}")
    print()

    assert result['overall_complete'] == False, "Empty data should be incomplete"
    assert result['overall_percentage'] < 20, "Empty data should have low percentage"
    print("✅ PASSED: Empty data correctly identified as incomplete\n")


def test_minimal_vague_data():
    """Test with minimal vague data - should be incomplete"""
    evaluator = ChecklistEvaluator()

    result = evaluator.evaluate_gathered_data({
        'locations': [],
        'facts': [
            {'content': 'A fantasy world', 'fact_category': 'current_state', 'what_type': 'general'}
        ]
    })

    print("=" * 60)
    print("TEST 2: Minimal Vague Data (1 fact, no locations)")
    print("=" * 60)
    print(f"Overall complete: {result['overall_complete']}")
    print(f"Overall percentage: {result['overall_percentage']}%")
    print(f"Satisfied: {result['satisfied_requirements']}")
    print(f"Missing: {[m['name'] for m in result['missing_requirements']]}")
    print(f"Next priority: {result['next_priority']}")
    print()

    assert result['overall_complete'] == False, "Vague data should be incomplete"
    print("✅ PASSED: Vague data correctly identified as incomplete\n")


def test_partial_data():
    """Test with partial good data - should be incomplete but higher percentage"""
    evaluator = ChecklistEvaluator()

    result = evaluator.evaluate_gathered_data({
        'locations': [
            {'name': 'Skyreach', 'location_type': 'city', 'relative_position': 'center'},
            {'name': 'Frostpeak', 'location_type': 'mountain', 'relative_position': 'far north'},
            {'name': 'Verdant Forest', 'location_type': 'forest', 'relative_position': 'south of Skyreach'}
        ],
        'facts': [
            {
                'content': 'Floating sky islands separated by toxic mist below',
                'fact_category': 'current_state',
                'what_type': 'geographic'
            },
            {
                'content': 'Ancient magical civilization built great towers',
                'fact_category': 'current_state',
                'what_type': 'geographic'
            },
            {
                'content': 'Magic is rare and corrupts users',
                'fact_category': 'world_rule',
                'what_type': 'cultural'
            },
            {
                'content': 'Magic can warp reality but costs humanity',
                'fact_category': 'world_rule',
                'what_type': 'cultural'
            }
        ]
    })

    print("=" * 60)
    print("TEST 3: Partial Data (3 locations, 4 facts)")
    print("=" * 60)
    print(f"Overall complete: {result['overall_complete']}")
    print(f"Overall percentage: {result['overall_percentage']}%")
    print(f"Satisfied: {result['satisfied_requirements']}")
    print(f"Missing: {[m['name'] for m in result['missing_requirements']]}")

    # Show what's satisfied
    for eval_item in result['fact_evaluations']:
        if eval_item['satisfied']:
            print(f"  ✅ {eval_item['name']}: {eval_item['count']}/{eval_item['required']}")

    print()

    assert result['overall_percentage'] > 30, "Partial data should have decent percentage"
    assert 'Locations' in result['satisfied_requirements'], "3 locations should satisfy requirement"
    print("✅ PASSED: Partial data correctly evaluated\n")


def test_complete_data():
    """Test with complete data - should be satisfied"""
    evaluator = ChecklistEvaluator()

    result = evaluator.evaluate_gathered_data({
        'locations': [
            {'name': 'Skyreach', 'location_type': 'city', 'relative_position': 'center'},
            {'name': 'Frostpeak', 'location_type': 'mountain', 'relative_position': 'far north'},
            {'name': 'Verdant Forest', 'location_type': 'forest', 'relative_position': 'south of Skyreach'}
        ],
        'facts': [
            # World Setting (2)
            {'content': 'Floating sky islands', 'fact_category': 'current_state', 'what_type': 'geographic'},
            {'content': 'Toxic mist below the islands', 'fact_category': 'current_state', 'what_type': 'geographic'},

            # Magic System (2)
            {'content': 'Magic is rare and corrupts users', 'fact_category': 'world_rule', 'what_type': 'cultural'},
            {'content': 'Magic can warp reality but costs humanity', 'fact_category': 'world_rule', 'what_type': 'cultural'},

            # Technology Level (1)
            {'content': 'Medieval technology with primitive airships', 'fact_category': 'current_state', 'what_type': 'structural'},

            # Major Conflict (1)
            {'content': 'Sky islands slowly falling as magic destabilizes', 'fact_category': 'current_state', 'what_type': 'political'},

            # History (1)
            {'content': 'Ancient civilization collapsed 500 years ago', 'fact_category': 'historical', 'what_type': 'cultural'},

            # Culture (1)
            {'content': 'Sky-dwellers view ground as cursed', 'fact_category': 'current_state', 'what_type': 'social'}
        ]
    })

    print("=" * 60)
    print("TEST 4: Complete Data (All Requirements Met)")
    print("=" * 60)
    print(f"Overall complete: {result['overall_complete']}")
    print(f"Overall percentage: {result['overall_percentage']}%")
    print(f"Satisfied: {result['satisfied_requirements']}")
    print(f"Missing: {result['missing_requirements']}")
    print(f"Next priority: {result['next_priority']}")
    print()

    # Show all satisfied items
    print("Satisfied requirements:")
    for eval_item in result['fact_evaluations']:
        status = "✅" if eval_item['satisfied'] else "❌"
        print(f"  {status} {eval_item['name']}: {eval_item['count']}/{eval_item['required']}")

    print()

    assert result['overall_complete'] == True, "Complete data should be satisfied"
    assert result['overall_percentage'] == 100, "Complete data should be 100%"
    assert result['next_priority'] == "All requirements satisfied", "Should indicate completion"
    print("✅ PASSED: Complete data correctly identified as satisfied\n")


def test_progress_report():
    """Test progress report generation"""
    evaluator = ChecklistEvaluator()

    data = {
        'locations': [
            {'name': 'Skyreach', 'location_type': 'city', 'relative_position': 'center'},
        ],
        'facts': [
            {'content': 'Floating sky islands', 'fact_category': 'current_state', 'what_type': 'geographic'},
            {'content': 'Magic is rare', 'fact_category': 'world_rule', 'what_type': 'cultural'},
        ]
    }

    print("=" * 60)
    print("TEST 5: Progress Report Generation")
    print("=" * 60)

    report = evaluator.generate_progress_report(data)
    print(report)

    assert "WORLD BUILDING PROGRESS" in report, "Report should have header"
    assert "MISSING REQUIREMENTS" in report, "Report should show missing items"
    print("✅ PASSED: Progress report generated correctly\n")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("CHECKLIST EVALUATOR TEST SUITE")
    print("=" * 60 + "\n")

    try:
        test_empty_data()
        test_minimal_vague_data()
        test_partial_data()
        test_complete_data()
        test_progress_report()

        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
