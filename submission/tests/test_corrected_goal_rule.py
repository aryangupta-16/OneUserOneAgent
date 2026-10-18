"""Tests for corrected goal rule handling."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.goals.goal_registry import load_goals, apply_goal_correction, is_goal_measurable
from src.state.viewer_state import ViewerStateManager


def test_g03_correction():
    """G03 correction changes success from app_open to play_started."""
    goals = load_goals(os.path.join(os.path.dirname(__file__),
        "..", "..", "docs", "one_user_one_agent_pack 2", "config", "goals.json"))
    g03 = next(g for g in goals if g["goal_id"] == "G03")
    assert g03["success"]["event"] == "app_open"
    old = g03["success"].copy()
    new = {"event": "play_started", "condition": "on a later IST calendar day within the window", "window_hours": 48}
    result = apply_goal_correction(goals, "G03", old, new)
    assert result is True
    g03_updated = next(g for g in goals if g["goal_id"] == "G03")
    assert g03_updated["success"]["event"] == "play_started"
    assert g03_updated.get("corrected") is True


def test_goal_correction_applied_to_state():
    """Goal correction should update open goals in viewer states."""
    mgr = ViewerStateManager()
    state = mgr.get_or_create("U-001")
    state.current_goal = {"id": "G03", "success": {"event": "app_open"}, "status": "open"}
    state.goal_history = [{"id": "G03", "status": "open", "success": {"event": "app_open"}}]
    mgr.apply_goal_correction("G03", {"event": "app_open"}, {"event": "play_started"})
    assert state.current_goal["success"]["event"] == "play_started"
    assert state.current_goal.get("corrected") is True


if __name__ == "__main__":
    test_g03_correction()
    test_goal_correction_applied_to_state()
    print("All corrected goal rule tests passed!")
