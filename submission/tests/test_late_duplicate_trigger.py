"""Tests for late and duplicate trigger handling."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from src.data.events import load_events, is_duplicate, compute_event_age, parse_ts
from src.state.viewer_state import ViewerStateManager, ViewerState
from src.config import IST


def test_duplicate_event_ignored():
    """Duplicate events (same event_id) should be ignored."""
    seen = set()
    e1 = {"event_id": "abc-123", "user_id": "U-001", "event": "app_open"}
    e2 = {"event_id": "abc-123", "user_id": "U-001", "event": "app_open"}
    assert not is_duplicate(e1, seen)
    seen.add("abc-123")
    assert is_duplicate(e2, seen)


def test_late_event_processed():
    """Events arriving late (large event_age) should still be processed."""
    event = {
        "event_id": "late-1",
        "user_id": "U-001",
        "event": "app_open",
        "occurred_at": "2026-09-28T10:00:00.000Z",
        "received_at": "2026-10-01T10:00:00.000Z",
        "sent_at": "2026-09-28T10:00:00.000Z",
    }
    age = compute_event_age(event)
    assert age > 86400 * 2  # More than 2 days old
    mgr = ViewerStateManager()
    state = mgr.update("U-001", event)
    assert len(state.events) == 1
    assert state.last_app_open is not None


def test_idempotent_reprocessing():
    """Processing the same event twice should not double-count."""
    mgr = ViewerStateManager()
    event = {
        "event_id": "idem-1",
        "user_id": "U-001",
        "event": "play_started",
        "occurred_at": "2026-10-01T10:00:00.000Z",
        "received_at": "2026-10-01T10:00:01.000Z",
        "properties": {"title_id": "T0001", "episode_id": "ep1"},
    }
    mgr.update("U-001", event)
    state = mgr.get_or_create("U-001")
    assert state.has_played is True
    # Process again (duplicate)
    mgr.update("U-001", event)
    # has_played should still be True (not toggled)
    assert state.has_played is True


if __name__ == "__main__":
    test_duplicate_event_ignored()
    test_late_event_processed()
    test_idempotent_reprocessing()
    print("All late/duplicate tests passed!")
