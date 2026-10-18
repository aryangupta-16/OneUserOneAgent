"""Orchestrate outcome judgment for all decisions."""
from __future__ import annotations

import json
from ..data.loader import DataPack
from ..goals.goal_judge import judge_goal


def judge_outcomes(decisions: list[dict], outcome_events: list[dict], pack: DataPack) -> list[dict]:
    """Judge outcomes for all decisions that have goals."""
    outcomes = []
    # Group decisions by user
    user_decisions: dict[str, list[dict]] = {}
    for d in decisions:
        uid = d.get("viewer_id", "")
        if uid not in user_decisions:
            user_decisions[uid] = []
        user_decisions[uid].append(d)

    for uid, decs in user_decisions.items():
        for d in decs:
            goal = d.get("goal")
            if not goal:
                continue
            goal_record = {
                "id": goal.get("id", ""),
                "user_id": uid,
                "deadline": goal.get("deadline", ""),
                "started_at": d.get("trigger", {}).get("received_at", ""),
                "success": _get_success_def(pack, goal.get("id", "")),
            }
            result = judge_goal(goal_record, outcome_events, pack)
            result["decision_id"] = d.get("decision_id", "")
            result["action"] = d.get("action", "NONE")
            outcomes.append(result)
    return outcomes


def _get_success_def(pack, goal_id):
    g = pack.get_goal_by_id(goal_id)
    if g:
        return g.get("success", {})
    return {}


def save_outcomes(outcomes, path):
    with open(path, "w", encoding="utf-8") as f:
        for o in outcomes:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
