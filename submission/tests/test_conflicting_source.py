"""Tests for conflicting source handling."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.state.viewer_state import ViewerState, ViewerStateManager
from src.state.fact_resolver import resolve_dialect, resolve_subscription
from src.config import VALID_DIALECTS


def test_dialect_conflict_resolution():
    """When app_dialect disagrees with profile, app_dialect wins."""
    state = ViewerState(user_id="U-001")
    state.dialect = "d1"  # Previous event said d1
    event = {"app_dialect": "d3", "properties": {}}
    dialect, conflicts = resolve_dialect(state, event)
    assert dialect == "d3"  # Current event wins


def test_dialect_na_fallback():
    """When app_dialect is 'NA', fall back to previous dialect."""
    state = ViewerState(user_id="U-001")
    state.dialect = "d2"
    event = {"app_dialect": "NA", "properties": {}}
    dialect, conflicts = resolve_dialect(state, event)
    assert dialect == "d2"  # Falls back to previous


def test_deeplink_dialect_conflict():
    """When deeplink dialect differs from app_dialect, conflict is recorded."""
    state = ViewerState(user_id="U-001")
    event = {
        "app_dialect": "d2",
        "properties": {"deeplink": "ott://c/cmp032/d5/title/T1901"},
    }
    dialect, conflicts = resolve_dialect(state, event)
    assert dialect == "d2"  # app_dialect wins
    assert len(conflicts) > 0  # But conflict is recorded


def test_subscription_conflict():
    """When events say active but profile says lapsed, events win."""
    state = ViewerState(user_id="U-001")
    state.subscription_status = "active"
    profile = {"subscription_status": "lapsed"}
    status, conflicts = resolve_subscription(state, profile)
    assert status == "active"
    assert len(conflicts) > 0


if __name__ == "__main__":
    test_dialect_conflict_resolution()
    test_dialect_na_fallback()
    test_deeplink_dialect_conflict()
    test_subscription_conflict()
    print("All conflicting source tests passed!")
