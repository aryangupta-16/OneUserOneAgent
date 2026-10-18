"""Tests for holdout isolation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.verify.verifier import verify_decision
from src.state.viewer_state import ViewerState
from src.data.loader import DataPack


def test_holdout_no_action():
    """Holdout users should get no actions."""
    state = ViewerState(user_id="U-001")
    state.arm = "holdout"
    decision = {"goal": None, "action": "home_page", "dialect": {"used": "d1"}, "content": []}
    pack_path = os.path.join(os.path.dirname(__file__),
        "..", "..", "docs", "one_user_one_agent_pack 2")
    if os.path.exists(pack_path):
        from datetime import datetime, timezone
        pack = DataPack(pack_path).load()
        now = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
        checks = verify_decision(decision, state, pack, now)
        assert "holdout_violation" in checks["failed"]


def test_holdout_no_action_passes():
    """Holdout users with no_action should pass verification."""
    state = ViewerState(user_id="U-001")
    state.arm = "holdout"
    decision = {"goal": None, "action": "none", "dialect": {"used": "d1"}, "content": []}
    pack_path = os.path.join(os.path.dirname(__file__),
        "..", "..", "docs", "one_user_one_agent_pack 2")
    if os.path.exists(pack_path):
        from datetime import datetime, timezone
        pack = DataPack(pack_path).load()
        now = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
        checks = verify_decision(decision, state, pack, now)
        assert "holdout_ok" in checks["passed"]
        assert "holdout_violation" not in checks["failed"]


if __name__ == "__main__":
    test_holdout_no_action()
    test_holdout_no_action_passes()
    print("All holdout isolation tests passed!")
