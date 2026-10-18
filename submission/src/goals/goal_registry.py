"""Goal loading, trap detection, and registry management."""
from __future__ import annotations

import json
from typing import Optional

from ..config import KNOWN_EVENT_TYPES

# Known event types that exist in the stream (for measurability check)
# tv_app_open is NOT in the event stream - G11 trap
MEASURABLE_EVENTS = KNOWN_EVENT_TYPES


def load_goals(path: str) -> list[dict]:
    """Load goals from goals.json and annotate with measurability."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    goals = data["goals"]
    for g in goals:
        g["is_measurable"] = is_goal_measurable(g)
    return goals


def is_goal_measurable(goal: dict) -> bool:
    """Check if a goal has a valid success signal in the event stream.

    Traps:
    - G10: event is null (meaningful_engagement has no measurable signal)
    - G11: event is tv_app_open (doesn't exist in event stream)
    """
    success = goal.get("success", {})
    event = success.get("event")

    # G10 trap: event is null
    if event is None:
        return False

    # G11 trap: tv_app_open doesn't exist in the event stream
    if event not in MEASURABLE_EVENTS:
        return False

    return True


def get_goal_by_id(goals: list[dict], goal_id: str) -> Optional[dict]:
    """Find a goal by its ID."""
    for g in goals:
        if g["goal_id"] == goal_id:
            return g
    return None


def get_measurable_goals(goals: list[dict]) -> list[dict]:
    """Filter goals to only those that are measurable."""
    return [g for g in goals if g.get("is_measurable", True)]


def apply_goal_correction(
    goals: list[dict],
    goal_id: str,
    old_success: dict,
    new_success: dict,
) -> bool:
    """Apply a mid-replay goal rule correction.

    Returns True if the goal was found and corrected.
    """
    for g in goals:
        if g["goal_id"] == goal_id:
            g["success"] = new_success
            g["corrected"] = True
            g["old_success"] = old_success
            # Re-check measurability after correction
            g["is_measurable"] = is_goal_measurable(g)
            return True
    return False
