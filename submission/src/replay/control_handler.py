"""Handle control events: title withdrawals, goal corrections, dependency failures."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..data.events import parse_ts
from ..data.catalogue import parse_available_time
from ..goals.goal_registry import apply_goal_correction


class ControlHandler:
    """Processes control events during the replay."""

    def __init__(self):
        self.withdrawn_titles: set[str] = set()
        self.model_unavailable: bool = False
        self.model_unavailable_until: Optional[datetime] = None
        self.data_store_degraded: bool = False
        self.data_store_degraded_until: Optional[datetime] = None
        self.corrections_applied: list[dict] = []

    def handle(self, event: dict, goals: list[dict], state_manager, catalogue: dict, now: datetime):
        """Process a single control event."""
        etype = event.get("type", "")
        at = parse_ts(event.get("at"))

        if etype == "title_withdrawn":
            tid = event.get("title_id", "")
            self.withdrawn_titles.add(tid)
            # Mark title as unavailable in catalogue
            if tid in catalogue:
                catalogue[tid]["available_until"] = event.get("at", "")
                catalogue[tid]["withdrawn"] = True

        elif etype == "goal_rule_corrected":
            gid = event.get("goal_id", "")
            old_s = event.get("old_success", {})
            new_s = event.get("new_success", {})
            apply_goal_correction(goals, gid, old_s, new_s)
            state_manager.apply_goal_correction(gid, old_s, new_s)
            self.corrections_applied.append({
                "goal_id": gid, "old": old_s, "new": new_s, "at": event.get("at"),
            })

        elif etype == "dependency_unavailable":
            dep = event.get("dependency", "")
            until = parse_ts(event.get("until"))
            if dep == "model_provider":
                self.model_unavailable = True
                self.model_unavailable_until = until

        elif etype == "dependency_degraded":
            dep = event.get("dependency", "")
            until = parse_ts(event.get("until"))
            if dep == "user_data_store":
                self.data_store_degraded = True
                self.data_store_degraded_until = until

    def update_time(self, now: datetime):
        """Check if any temporary failures have expired."""
        if self.model_unavailable and self.model_unavailable_until:
            if now >= self.model_unavailable_until:
                self.model_unavailable = False
                self.model_unavailable_until = None
        if self.data_store_degraded and self.data_store_degraded_until:
            if now >= self.data_store_degraded_until:
                self.data_store_degraded = False
                self.data_store_degraded_until = None

    def is_model_available(self) -> bool:
        return not self.model_unavailable

    def is_data_store_ok(self) -> bool:
        return not self.data_store_degraded
