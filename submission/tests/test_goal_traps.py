"""Tests for goal traps (G10, G11)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.goals.goal_registry import load_goals, is_goal_measurable, get_measurable_goals


def test_g10_not_measurable():
    """G10 (meaningful_engagement) has event=null - not measurable."""
    goals = load_goals(os.path.join(os.path.dirname(__file__),
        "..", "..", "docs", "one_user_one_agent_pack 2", "config", "goals.json"))
    g10 = next(g for g in goals if g["goal_id"] == "G10")
    assert g10["is_measurable"] is False


def test_g11_not_measurable():
    """G11 (tv_activation) has event=tv_app_open which doesn't exist in stream."""
    goals = load_goals(os.path.join(os.path.dirname(__file__),
        "..", "..", "docs", "one_user_one_agent_pack 2", "config", "goals.json"))
    g11 = next(g for g in goals if g["goal_id"] == "G11")
    assert g11["is_measurable"] is False


def test_measurable_goals_exclude_traps():
    """get_measurable_goals should exclude G10 and G11."""
    goals = load_goals(os.path.join(os.path.dirname(__file__),
        "..", "..", "docs", "one_user_one_agent_pack 2", "config", "goals.json"))
    measurable = get_measurable_goals(goals)
    ids = {g["goal_id"] for g in measurable}
    assert "G10" not in ids
    assert "G11" not in ids
    assert "G01" in ids
    assert len(measurable) == 10  # 12 - 2 traps


if __name__ == "__main__":
    test_g10_not_measurable()
    test_g11_not_measurable()
    test_measurable_goals_exclude_traps()
    print("All goal trap tests passed!")
