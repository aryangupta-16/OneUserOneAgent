"""Real OpenAI model provider with fallback to mock."""
from __future__ import annotations

import json
import os
from typing import Optional

from .mock_provider import MockModelProvider, ModelError


class OpenAIModelProvider:
    """Real OpenAI model provider for goal selection and content reasoning.

    Falls back to MockModelProvider when OPENAI_API_KEY is not set.
    """

    def __init__(self, model_faults: list[dict], dependency_state: Optional[dict] = None):
        self._mock = MockModelProvider(model_faults, dependency_state)
        self._client = None
        self._model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self._use_real = False
        self.call_count = 0

        # Try to initialize real OpenAI client
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=api_key)
                self._use_real = True
            except ImportError:
                print("Warning: openai package not installed. Using mock provider.")
                print("Install with: pip install openai")
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI client: {e}. Using mock provider.")

    def set_dependency_state(self, state: dict):
        self._mock.set_dependency_state(state)
        if state.get("model_unavailable"):
            self._use_real = False  # Force mock during outages

    def call(self, trigger_event_id: str, user_id: str, context: dict) -> dict:
        """Call the model. Uses real OpenAI if available, otherwise mock."""
        self.call_count += 1

        # Always check for faults first (even with real LLM)
        fault = self._mock._faults_by_trigger.get(trigger_event_id)
        if fault:
            return self._mock._reproduce_fault(fault)

        # Check dependency state
        if self._mock._dependency_state.get("model_unavailable"):
            raise ModelError("Model provider unavailable (HTTP 503)")

        # Use real LLM if available
        if self._use_real and self._client:
            try:
                return self._call_real(trigger_event_id, user_id, context)
            except Exception as e:
                print(f"Warning: Real LLM call failed: {e}. Falling back to mock.")
                return self._mock._safe_default(user_id, context)

        # Fallback to mock
        return self._mock._safe_default(user_id, context)

    def _call_real(self, trigger_event_id: str, user_id: str, context: dict) -> dict:
        """Make a real OpenAI API call for goal selection reasoning."""
        goal = context.get("goal", {})
        dialect = context.get("dialect", "unknown")
        subscription = context.get("subscription", "unknown")

        prompt = f"""You are an AI agent for an OTT streaming platform. A viewer just opened the app.

Viewer context:
- User ID: {user_id}
- Dialect: {dialect}
- Subscription: {subscription}
- Selected goal: {goal.get('name', 'unknown')} ({goal.get('id', '')})
- Goal description: {goal.get('description', '')}

Based on this context, should the agent:
1. Confirm this goal is appropriate for this viewer? (yes/no)
2. What confidence level? (0.0 to 1.0)
3. Brief reason (one sentence)

Respond in JSON format:
{{"eligible": true/false, "confidence": 0.0-1.0, "reason": "...", "goal_id": "..."}}"""

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )

        content = response.choices[0].message.content.strip()
        # Parse JSON from response
        try:
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)
            result["goal_id"] = goal.get("id", "")
            return result
        except json.JSONDecodeError:
            return {"eligible": False, "confidence": 0.0, "reason": "parse_error", "goal_id": goal.get("id")}
