"""Mock model provider that reproduces model_faults.jsonl and returns rule-based responses."""
from __future__ import annotations

import time
from typing import Optional

from .provider import ModelError


class MockModelProvider:
    """Mock model provider that reproduces faults and returns safe defaults.

    For triggers listed in model_faults.jsonl, it reproduces the exact fault.
    For all other triggers, it returns a safe rule-based response.
    """

    def __init__(self, model_faults: list[dict], dependency_state: Optional[dict] = None):
        self._faults_by_trigger = {}
        for fault in model_faults:
            tid = fault.get("trigger_event_id")
            if tid:
                self._faults_by_trigger[tid] = fault
        self._dependency_state = dependency_state or {}
        self.call_count = 0

    def set_dependency_state(self, state: dict):
        """Update dependency state (for simulating outages/degradation)."""
        self._dependency_state = state

    def call(self, trigger_event_id: str, user_id: str, context: dict) -> dict:
        """Call the mock model.

        Reproduces faults from model_faults.jsonl for specific triggers.
        Otherwise returns a safe default response.
        """
        self.call_count += 1

        # Check if model provider is unavailable
        if self._dependency_state.get("model_unavailable"):
            raise ModelError("Model provider unavailable (HTTP 503)")

        # Check for specific trigger faults
        fault = self._faults_by_trigger.get(trigger_event_id)
        if fault:
            return self._reproduce_fault(fault)

        # Safe default response
        return self._safe_default(user_id, context)

    def _reproduce_fault(self, fault: dict) -> dict:
        """Reproduce a specific model fault."""
        fault_type = fault.get("fault", "")

        if fault_type == "timeout":
            seconds = fault.get("seconds", 45)
            time.sleep(min(seconds, 2))  # Cap actual sleep for testing
            raise TimeoutError(f"Model timeout after {seconds}s")

        elif fault_type == "unsupported_claim":
            # Return the model's unsupported output - the agent must verify this
            return fault.get("model_output", {})

        elif fault_type == "malformed_output":
            raw = fault.get("model_output", "")
            # Return the malformed string - agent must handle parse failure
            return {"_raw": raw, "_malformed": True}

        return self._safe_default(fault.get("user_id", ""), {})

    def _safe_default(self, user_id: str, context: dict) -> dict:
        """Return a safe, conservative default response."""
        return {
            "eligible": False,
            "confidence": 0.0,
            "reason": "mock_default: no model call needed",
            "goal_id": None,
        }
