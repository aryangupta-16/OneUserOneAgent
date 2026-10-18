"""Agent vs holdout comparison with honest attribution."""
from __future__ import annotations

import json
from ..data.loader import DataPack


def compute_impact(decisions, outcomes, pack):
    """Compare agent arm vs holdout arm using randomized assignment.

    IMPORTANT: We compare by ARM (randomized), not by served/unserved.
    """
    arms = pack.arms
    agent_users = {uid for uid, arm in arms.items() if arm == "agent"}
    holdout_users = {uid for uid, arm in arms.items() if arm == "holdout"}

    # Group outcomes by arm
    agent_outcomes = [o for o in outcomes if o.get("user_id") in agent_users]
    holdout_outcomes = [o for o in outcomes if o.get("user_id") in holdout_users]

    # Count successes
    agent_total = len(agent_outcomes)
    agent_success = sum(1 for o in agent_outcomes if o.get("status") == "succeeded")
    holdout_total = len(holdout_outcomes)
    holdout_success = sum(1 for o in holdout_outcomes if o.get("status") == "succeeded")

    agent_rate = agent_success / agent_total if agent_total else 0
    holdout_rate = holdout_success / holdout_total if holdout_total else 0
    uplift = agent_rate - holdout_rate
    ratio = agent_rate / holdout_rate if holdout_rate > 0 else 0

    # Per-goal breakdown
    goal_breakdown = {}
    for o in outcomes:
        gid = o.get("goal_id", "")
        uid = o.get("user_id", "")
        arm = arms.get(uid, "unknown")
        if gid not in goal_breakdown:
            goal_breakdown[gid] = {"agent": {"total": 0, "success": 0},
                                   "holdout": {"total": 0, "success": 0}}
        if arm in goal_breakdown[gid]:
            goal_breakdown[gid][arm]["total"] += 1
            if o.get("status") == "succeeded":
                goal_breakdown[gid][arm]["success"] += 1

    return {
        "agent_arm": {"users": len(agent_users), "goals": agent_total,
                      "succeeded": agent_success, "rate": round(agent_rate, 4)},
        "holdout_arm": {"users": len(holdout_users), "goals": holdout_total,
                        "succeeded": holdout_success, "rate": round(holdout_rate, 4)},
        "uplift_absolute": round(uplift, 4),
        "uplift_relative": round(ratio, 4),
        "method": "agent_arm_vs_holdout_arm (randomized)",
        "note": "Compared by randomized arm assignment, NOT by served vs unserved",
        "goal_breakdown": goal_breakdown,
    }


def write_impact_report(impact, path):
    """Write impact_report.md."""
    lines = [
        "# Impact Report",
        "",
        "## Method",
        "",
        f"**{impact['method']}**",
        f"{impact['note']}",
        "",
        "## Results",
        "",
        "| Group | Users | Goals Tracked | Succeeded | Rate |",
        "|---|---|---|---|---|",
        f"| Agent | {impact['agent_arm']['users']} | {impact['agent_arm']['goals']} | {impact['agent_arm']['succeeded']} | {impact['agent_arm']['rate']:.1%} |",
        f"| Holdout | {impact['holdout_arm']['users']} | {impact['holdout_arm']['goals']} | {impact['holdout_arm']['succeeded']} | {impact['holdout_arm']['rate']:.1%} |",
        "",
        f"**Absolute uplift:** {impact['uplift_absolute']:.1%}",
        f"**Relative uplift:** {impact['uplift_relative']:.2f}x",
        "",
        "## Per-Goal Breakdown",
        "",
        "| Goal | Agent Rate | Holdout Rate |",
        "|---|---|---|",
    ]
    for gid, data in sorted(impact.get("goal_breakdown", {}).items()):
        ar = data["agent"]["success"] / data["agent"]["total"] if data["agent"]["total"] else 0
        hr = data["holdout"]["success"] / data["holdout"]["total"] if data["holdout"]["total"] else 0
        lines.append(f"| {gid} | {ar:.1%} ({data['agent']['success']}/{data['agent']['total']}) | {hr:.1%} ({data['holdout']['success']}/{data['holdout']['total']}) |")

    lines.extend(["", "## Why Not Served vs Unserved?", ""])
    lines.append("Comparing 'served' vs 'unserved' users introduces survivorship bias.")
    lines.append("Users the agent chose to help were already more likely to succeed.")
    lines.append("The randomized holdout arm provides an unbiased comparison.")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
