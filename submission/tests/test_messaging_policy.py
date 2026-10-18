"""Tests for messaging policy enforcement."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from src.config import IST, QUIET_HOURS_START, QUIET_HOURS_END
from src.agent.intervention_builder import _is_quiet_hours, _can_send_push, _can_send_whatsapp
from src.state.viewer_state import ViewerState


def test_quiet_hours_detected():
    """Messages during 22:00-08:00 IST should be blocked."""
    # 23:00 IST = 17:30 UTC
    dt = datetime(2026, 10, 1, 17, 30, tzinfo=timezone.utc)
    assert _is_quiet_hours(dt) is True
    # 07:00 IST = 01:30 UTC
    dt2 = datetime(2026, 10, 1, 1, 30, tzinfo=timezone.utc)
    assert _is_quiet_hours(dt2) is True


def test_non_quiet_hours():
    """Messages during 08:00-22:00 IST should be allowed."""
    # 12:00 IST = 06:30 UTC
    dt = datetime(2026, 10, 1, 6, 30, tzinfo=timezone.utc)
    assert _is_quiet_hours(dt) is False


def test_push_blocked_without_consent():
    """Push should be blocked when notifications_opt_in is False."""
    state = ViewerState(user_id="U-001")
    state.consent["notifications_opt_in"] = False
    dt = datetime(2026, 10, 1, 6, 30, tzinfo=timezone.utc)
    assert _can_send_push(state, dt) is False


def test_whatsapp_blocked_without_consent():
    """WhatsApp should be blocked when whatsapp_opt_in is False."""
    state = ViewerState(user_id="U-001")
    state.consent["whatsapp_opt_in"] = False
    dt = datetime(2026, 10, 1, 6, 30, tzinfo=timezone.utc)
    assert _can_send_whatsapp(state, dt) is False


def test_frequency_cap():
    """Only 1 push/whatsapp per IST day."""
    state = ViewerState(user_id="U-001")
    state.consent["notifications_opt_in"] = True
    dt = datetime(2026, 10, 1, 6, 30, tzinfo=timezone.utc)
    state.last_message_day = dt.astimezone(IST).strftime("%Y-%m-%d")
    assert _can_send_push(state, dt) is False


if __name__ == "__main__":
    test_quiet_hours_detected()
    test_non_quiet_hours()
    test_push_blocked_without_consent()
    test_whatsapp_blocked_without_consent()
    test_frequency_cap()
    print("All messaging policy tests passed!")
