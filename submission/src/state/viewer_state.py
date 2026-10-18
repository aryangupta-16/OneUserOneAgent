"""Per-viewer state management with durable facts and provenance."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from ..data.events import parse_ts


@dataclass
class ViewerFact:
    """A single fact about a viewer with provenance tracking."""
    value: Any
    source: str  # "event", "profile", "app_setting", "deeplink"
    event_id: Optional[str] = None
    received_at: Optional[datetime] = None
    occurred_at: Optional[datetime] = None
    freshness_s: float = 0.0


@dataclass
class ViewerState:
    """Complete per-viewer state with durable facts and history."""
    user_id: str
    facts: dict[str, ViewerFact] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    current_goal: Optional[dict] = None
    goal_history: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    last_message_day: Optional[str] = None
    consent: dict = field(default_factory=lambda: {
        "notifications_opt_in": True,
        "whatsapp_opt_in": True,
    })
    dialect: str = ""
    dialect_conflicts: list[dict] = field(default_factory=list)
    subscription_status: str = "never"
    arm: str = "holdout"
    signup_at: Optional[datetime] = None
    platform: str = "android"
    seen_event_ids: set[str] = field(default_factory=set)
    has_played: bool = False
    has_completed_episode: bool = False
    has_purchased: bool = False
    last_app_open: Optional[datetime] = None
    plays_by_day: set[str] = field(default_factory=set)
    unfinished_slugs: dict[str, dict] = field(default_factory=dict)
    last_play_at: Optional[datetime] = None
    goal_corrections: list[dict] = field(default_factory=list)


class ViewerStateManager:
    """Manages durable per-viewer state across the replay."""

    def __init__(self):
        self.states: dict[str, ViewerState] = {}

    def get_or_create(self, user_id: str) -> ViewerState:
        if user_id not in self.states:
            self.states[user_id] = ViewerState(user_id=user_id)
        return self.states[user_id]

    def update(self, user_id: str, event: dict) -> ViewerState:
        state = self.get_or_create(user_id)
        event_type = event.get("event", "")
        received_at = parse_ts(event.get("received_at"))
        occurred_at = parse_ts(event.get("occurred_at"))
        eid = event.get("event_id", "")
        if eid:
            state.seen_event_ids.add(eid)
        state.events.append(event)
        app_dialect = event.get("app_dialect", "")
        if app_dialect and app_dialect != "NA":
            state.facts["dialect"] = ViewerFact(
                value=app_dialect, source="app_setting",
                event_id=eid, received_at=received_at, occurred_at=occurred_at)
            state.dialect = app_dialect
        props = event.get("properties", {})
        if event_type == "notification_opt_out":
            ch = props.get("channel", "")
            if ch == "push":
                state.consent["notifications_opt_in"] = False
            elif ch == "whatsapp":
                state.consent["whatsapp_opt_in"] = False
        if event_type == "signup_completed":
            state.signup_at = occurred_at or received_at
        elif event_type == "app_open":
            state.last_app_open = occurred_at or received_at
        elif event_type == "play_started":
            state.has_played = True
            state.last_play_at = occurred_at or received_at
            if occurred_at:
                from ..config import IST
                state.plays_by_day.add(occurred_at.astimezone(IST).strftime("%Y-%m-%d"))
        elif event_type == "episode_completed":
            state.has_completed_episode = True
        elif event_type == "purchase_completed":
            state.has_purchased = True
            if not props.get("is_trial", False):
                state.subscription_status = "active"
        elif event_type == "subscription_lapsed":
            state.subscription_status = "lapsed"
        elif event_type == "subscription_renewed":
            state.subscription_status = "active"
        elif event_type == "message_delivered" and props.get("channel") in ("push", "whatsapp"):
            if received_at:
                from ..config import IST
                state.last_message_day = received_at.astimezone(IST).strftime("%Y-%m-%d")
        return state

    def snapshot(self, user_id: str) -> dict:
        state = self.get_or_create(user_id)
        return {
            "user_id": state.user_id, "dialect": state.dialect,
            "dialect_conflicts": state.dialect_conflicts,
            "subscription_status": state.subscription_status, "arm": state.arm,
            "consent": state.consent, "has_played": state.has_played,
            "has_completed_episode": state.has_completed_episode,
            "has_purchased": state.has_purchased, "current_goal": state.current_goal,
            "goal_history": state.goal_history, "decision_count": len(state.decisions),
            "action_count": len(state.actions), "event_count": len(state.events),
        }

    def apply_goal_correction(self, goal_id, old_success, new_success):
        for state in self.states.values():
            if state.current_goal and state.current_goal.get("id") == goal_id:
                state.current_goal["success"] = new_success
                state.current_goal["corrected"] = True
                state.goal_corrections.append(
                    {"goal_id": goal_id, "old_success": old_success, "new_success": new_success})
            for gh in state.goal_history:
                if gh.get("id") == goal_id and gh.get("status") == "open":
                    gh["success"] = new_success
                    gh["corrected"] = True

    goal_corrections: list[dict] = field(default_factory=list)
