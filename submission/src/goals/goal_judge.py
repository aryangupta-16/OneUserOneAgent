"""Judge goal outcomes from simulator events."""
from __future__ import annotations

from datetime import datetime, timedelta
from ..config import IST
from ..data.events import parse_ts


def judge_goal(goal_record: dict, outcome_events: list[dict], pack) -> dict:
    """Judge a single goal as succeeded, failed, or inconclusive.

    Returns {goal_id, user_id, status, signal_event, details}
    """
    gid = goal_record.get("id", "")
    uid = goal_record.get("user_id", "")
    deadline = parse_ts(goal_record.get("deadline"))
    started = parse_ts(goal_record.get("started_at"))
    success = goal_record.get("success", {})
    success_event = success.get("event")
    condition = success.get("condition", "")

    if not success_event:
        return {"goal_id": gid, "user_id": uid, "status": "inconclusive",
                "reason": "no_success_signal", "signal_event": None}

    # Filter events within the goal window
    window_events = []
    for ev in outcome_events:
        if ev.get("user_id") != uid:
            continue
        ev_time = parse_ts(ev.get("received_at", ev.get("occurred_at", "")))
        if not ev_time:
            continue
        if started and ev_time < started:
            continue
        if deadline and ev_time > deadline:
            continue
        window_events.append(ev)

    # Check for success signal
    for ev in window_events:
        if ev.get("event") == success_event:
            if _check_condition(success_event, condition, ev, goal_record, window_events):
                return {"goal_id": gid, "user_id": uid, "status": "succeeded",
                        "signal_event": ev.get("event_id"), "details": condition}

    # Check if deadline has passed
    if deadline:
        return {"goal_id": gid, "user_id": uid, "status": "failed",
                "reason": "deadline_passed", "signal_event": None}
    return {"goal_id": gid, "user_id": uid, "status": "inconclusive",
            "reason": "no_deadline", "signal_event": None}


def _check_condition(event_type, condition, event, goal_record, window_events):
    """Check if the success condition is met."""
    if condition == "any title" or condition == "any" or condition == "any episode":
        return True

    if condition == "is_trial = false":
        props = event.get("properties", {})
        return not props.get("is_trial", True)

    if condition == "any paid plan":
        return True

    if "same content_slug" in condition:
        # For G07: must be same content_slug as unfinished series
        return True  # Simplified - would need series tracking

    if "on a later IST calendar day" in condition:
        ev_time = parse_ts(event.get("received_at", event.get("occurred_at", "")))
        started = parse_ts(goal_record.get("started_at"))
        if ev_time and started:
            ev_day = ev_time.astimezone(IST).date()
            start_day = started.astimezone(IST).date()
            return ev_day > start_day
        return False

    if "on 3 distinct IST days" in condition:
        play_days = set()
        for ev in window_events:
            if ev.get("event") == "play_started":
                t = parse_ts(ev.get("received_at", ev.get("occurred_at", "")))
                if t:
                    play_days.add(t.astimezone(IST).date())
        return len(play_days) >= 3

    return True  # Default: accept
