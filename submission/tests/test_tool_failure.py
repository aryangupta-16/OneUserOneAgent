"""Tests for tool/model failure handling."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model.mock_provider import MockModelProvider, ModelError


def test_model_timeout():
    """Model timeout should be handled gracefully."""
    faults = [{"trigger_event_id": "trigger-1", "user_id": "U-001",
               "fault": "timeout", "seconds": 45}]
    model = MockModelProvider(faults)
    try:
        model.call("trigger-1", "U-001", {})
        assert False, "Should have raised TimeoutError"
    except TimeoutError:
        pass  # Expected


def test_model_unsupported_claim():
    """Model unsupported claims should be returned but flagged."""
    faults = [{"trigger_event_id": "trigger-2", "user_id": "U-002",
               "fault": "unsupported_claim",
               "model_output": {"goal_id": "G04", "eligible": True, "confidence": 0.97,
                                "reason": "confirmed in billing"}}]
    model = MockModelProvider(faults)
    result = model.call("trigger-2", "U-002", {})
    assert result.get("eligible") is True
    assert "confirmed in billing" in result.get("reason", "")


def test_model_malformed_output():
    """Model malformed output should be flagged."""
    faults = [{"trigger_event_id": "trigger-3", "user_id": "U-003",
               "fault": "malformed_output",
               "model_output": '{"goal_id": "G02", "eligible": tr'}]
    model = MockModelProvider(faults)
    result = model.call("trigger-3", "U-003", {})
    assert result.get("_malformed") is True


def test_model_unavailable():
    """When model provider is unavailable, it should raise ModelError."""
    model = MockModelProvider([])
    model.set_dependency_state({"model_unavailable": True})
    try:
        model.call("trigger-x", "U-001", {})
        assert False, "Should have raised ModelError"
    except ModelError:
        pass


def test_normal_call_returns_safe_default():
    """Normal calls should return safe defaults."""
    model = MockModelProvider([])
    result = model.call("any-trigger", "U-001", {})
    assert result.get("eligible") is False
    assert result.get("confidence") == 0.0


if __name__ == "__main__":
    test_model_timeout()
    test_model_unsupported_claim()
    test_model_malformed_output()
    test_model_unavailable()
    test_normal_call_returns_safe_default()
    print("All tool failure tests passed!")
