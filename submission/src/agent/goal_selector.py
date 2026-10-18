"""Goal ranking and selection logic."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..state.viewer_state import ViewerState
from ..data.loader import DataPack
from ..goals.eligibility import check_eligibility
from ..goals.goal_registry import get_measurable_goals


def select_goal(state: ViewerState, pack: DataPack, now: datetime, profile=None):
    """Pick the best eligible goal for a viewer.

    Returns (goal_dict, evidence_refs) or (None, []) if no valid goal.
    """
    # If viewer already has an active goal, keep it (unless it expired)
    if state.current_goal:
        deadline = state.current_goal.get("deadline")
        if deadline:
            from ..data.events import parse_ts
            dl = parse_ts(deadline)
            if dl and now < dl:
                return state.current_goal, [f"existing_goal:{state.current_goal['id']}"]

    # Get measurable goals only (filters out G10, G11)
    measurable = get_measurable_goals(pack.goals)

    # Check eligibility for each goal
    candidates = []
    for goal in measurable:
        eligible, evidence = check_eligibility(goal, state, now, profile)
        if eligible:
            candidates.append((goal, evidence))

    if not candidates:
        return None, []

    # Rank candidates by priority
    # Priority order based on business impact:
    # 1. New user activation (G01, G03) - highest priority for retention
    # 2. First engagement (G02) - getting them to finish something
    # 3. Trial conversion (G04) - revenue
    # 4. First paid (G05) - revenue
    # 5. Reactivation (G06, G12) - win-back
    # 6. Engagement deepening (G07, G08, G09) - retention
    priority = {
        "G01": 1, "G03": 2, "G02": 3, "G04": 4, "G05": 5,
        "G06": 6, "G12": 7, "G07": 8, "G08": 9, "G09": 10,
    }

    candidates.sort(key=lambda c: priority.get(c[0]["goal_id"], 99))
    best_goal, best_evidence = candidates[0]

    # Build goal record with deadline
    window_hours = best_goal.get("success", {}).get("window_hours", 168)
    from datetime import timedelta
    deadline = now + timedelta(hours=window_hours)

    goal_record = {
        "id": best_goal["goal_id"],
        "name": best_goal["name"],
        "deadline": deadline.isoformat(),
        "success": best_goal.get("success", {}),
        "started_at": now.isoformat(),
        "status": "open",
    }

    return goal_record, best_evidence
