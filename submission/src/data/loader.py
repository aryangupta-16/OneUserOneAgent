"""DataPack: loads all files from the assignment data pack into indexed structures."""
from __future__ import annotations

import csv
import json
import os
from typing import Optional

from .events import load_events, build_user_event_index
from .catalogue import load_catalogue, load_episodes


class DataPack:
    """Holds all loaded and indexed data from the assignment pack."""

    def __init__(self, pack_path: str):
        self.pack_path = pack_path
        self.events_by_user: dict[str, list[dict]] = {}
        self.all_events: list[dict] = []
        self.profiles: dict[str, dict] = {}
        self.catalogue: dict[str, dict] = {}
        self.episodes: dict[str, list[dict]] = {}
        self.goals: list[dict] = []
        self.interventions: dict = {}
        self.pricing: dict = {}
        self.arms: dict[str, str] = {}
        self.triggers: list[dict] = []
        self.live_events: list[dict] = []
        self.control_events: list[dict] = []
        self.model_faults: list[dict] = []
        self._model_faults_by_trigger: dict[str, dict] = {}

    def load(self) -> "DataPack":
        """Load all data files from the pack directory."""
        p = self.pack_path

        # Data files
        self.all_events = load_events(os.path.join(p, "data", "events.jsonl"))
        self.events_by_user = build_user_event_index(self.all_events)
        self._load_profiles(os.path.join(p, "data", "profiles_snapshot.csv"))
        self.catalogue = load_catalogue(os.path.join(p, "data", "catalogue.csv"))
        self.episodes = load_episodes(os.path.join(p, "data", "episodes.csv"))

        # Config files
        with open(os.path.join(p, "config", "goals.json"), encoding="utf-8") as f:
            self.goals = json.load(f)["goals"]
        with open(os.path.join(p, "config", "interventions.json"), encoding="utf-8") as f:
            self.interventions = json.load(f)
        with open(os.path.join(p, "config", "pricing.json"), encoding="utf-8") as f:
            self.pricing = json.load(f)

        # Replay files
        self.triggers = self._load_jsonl(os.path.join(p, "replay", "triggers.jsonl"))
        self.live_events = self._load_jsonl(os.path.join(p, "replay", "live_events.jsonl"))
        self.control_events = self._load_jsonl(os.path.join(p, "replay", "control_events.jsonl"))
        self.model_faults = self._load_jsonl(os.path.join(p, "replay", "model_faults.jsonl"))
        self._load_arms(os.path.join(p, "replay", "arms.csv"))

        # Index model faults by trigger_event_id
        for fault in self.model_faults:
            tid = fault.get("trigger_event_id")
            if tid:
                self._model_faults_by_trigger[tid] = fault

        return self

    def _load_profiles(self, path: str):
        """Load profiles, keeping the most recent row per user_id."""
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                uid = row["user_id"]
                existing = self.profiles.get(uid)
                if existing is None or row["updated_at"] > existing["updated_at"]:
                    self.profiles[uid] = row

    def _load_arms(self, path: str):
        """Load randomized arms (agent/holdout) per user."""
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.arms[row["user_id"]] = row["arm"]

    def _load_jsonl(self, path: str) -> list[dict]:
        """Load a JSONL file."""
        items = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
        return items

    # --- Convenience methods ---

    def get_user_history(self, user_id: str) -> list[dict]:
        """Get all historical events for a user, sorted by received_at."""
        return self.events_by_user.get(user_id, [])

    def get_title(self, title_id: str) -> Optional[dict]:
        """Get a title by title_id."""
        return self.catalogue.get(title_id)

    def get_titles_for_dialect(self, dialect: str) -> list[dict]:
        """Get all titles available in a dialect."""
        return [t for t in self.catalogue.values() if t["dialect"] == dialect]

    def is_holdout(self, user_id: str) -> bool:
        """Check if a user is in the holdout arm."""
        return self.arms.get(user_id) == "holdout"

    def get_arm(self, user_id: str) -> str:
        """Get the arm for a user ('agent' or 'holdout')."""
        return self.arms.get(user_id, "holdout")

    def get_profile(self, user_id: str) -> Optional[dict]:
        """Get the profile snapshot for a user."""
        return self.profiles.get(user_id)

    def get_model_fault(self, trigger_event_id: str) -> Optional[dict]:
        """Get the model fault for a specific trigger, if any."""
        return self._model_faults_by_trigger.get(trigger_event_id)

    def get_episodes_for_slug(self, content_slug: str) -> list[dict]:
        """Get episodes for a content slug."""
        return self.episodes.get(content_slug, [])

    def get_goal_by_id(self, goal_id: str) -> Optional[dict]:
        """Get a goal definition by goal_id."""
        for g in self.goals:
            if g["goal_id"] == goal_id:
                return g
        return None

    def get_plan(self, plan_id: str) -> Optional[dict]:
        """Get a pricing plan by plan_id."""
        for plan in self.pricing.get("plans", []):
            if plan["plan_id"] == plan_id:
                return plan
        return None
