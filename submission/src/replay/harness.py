"""Replay harness: merges event streams and processes triggers through the agent."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from ..config import IST, UTC
from ..data.loader import DataPack
from ..data.events import parse_ts
from ..state.viewer_state import ViewerStateManager
from ..agent.decision_engine import DecisionEngine
from ..model.openai_provider import OpenAIModelProvider
from .control_handler import ControlHandler
from .latency_tracker import LatencyTracker


def merge_event_streams(triggers, live_events, control_events):
    """Merge all event streams by delivery time. Returns sorted list of (time, type, event)."""
    merged = []
    for e in triggers:
        t = parse_ts(e.get("deliver_at", e.get("received_at", "")))
        if t:
            merged.append((t, "trigger", e))
    for e in live_events:
        t = parse_ts(e.get("deliver_at", e.get("received_at", "")))
        if t:
            merged.append((t, "live", e))
    for e in control_events:
        t = parse_ts(e.get("at", ""))
        if t:
            merged.append((t, "control", e))
    merged.sort(key=lambda x: x[0])
    return merged


class ReplayHarness:
    """Orchestrates the full replay."""

    def __init__(self, pack: DataPack):
        self.pack = pack
        self.state_mgr = ViewerStateManager()
        self.model = OpenAIModelProvider(pack.model_faults)
        self.engine = DecisionEngine(pack, self.model)
        self.control = ControlHandler()
        self.latency = LatencyTracker()
        self.all_decisions: list[dict] = []
        self.all_actions: list[dict] = []

    def run(self):
        """Run the full replay."""
        # Initialize viewer states from historical data
        self._init_states()

        # Merge all event streams
        merged = merge_event_streams(
            self.pack.triggers, self.pack.live_events, self.pack.control_events)

        # Process events in order
        for ts, etype, event in merged:
            # Update dependency state
            self.control.update_time(ts)
            self.model.set_dependency_state({
                "model_unavailable": not self.control.is_model_available(),
            })

            if etype == "control":
                self.control.handle(event, self.pack.goals, self.state_mgr,
                                    self.pack.catalogue, ts)

            elif etype == "live":
                uid = event.get("user_id", "")
                if uid:
                    self.state_mgr.update(uid, event)

            elif etype == "trigger":
                uid = event.get("user_id", "")
                if not uid:
                    continue
                state = self.state_mgr.get_or_create(uid)
                state.arm = self.pack.get_arm(uid)

                # Load profile if available
                profile = self.pack.get_profile(uid)
                if profile and not state.signup_at:
                    state.signup_at = parse_ts(profile.get("signup_at"))
                    state.subscription_status = profile.get("subscription_status", "never")
                    state.consent["notifications_opt_in"] = profile.get("notifications_opt_in", "true") == "true"
                    state.consent["whatsapp_opt_in"] = profile.get("whatsapp_opt_in", "true") == "true"
                    if not state.dialect:
                        state.dialect = profile.get("preferred_dialect", "")

                # Process trigger through the agent
                decision, actions = self.engine.process_trigger(event, state, ts)
                self.all_decisions.append(decision)
                self.all_actions.extend(actions)
                self.latency.record(decision["decision_id"],
                                    decision["decided_in_ms"],
                                    event.get("deliver_at", ""))

    def _init_states(self):
        """Pre-load historical events into viewer states."""
        for uid, events in self.pack.events_by_user.items():
            state = self.state_mgr.get_or_create(uid)
            state.arm = self.pack.get_arm(uid)
            profile = self.pack.get_profile(uid)
            if profile:
                state.signup_at = parse_ts(profile.get("signup_at"))
                state.subscription_status = profile.get("subscription_status", "never")
                state.dialect = profile.get("preferred_dialect", "")
                state.consent["notifications_opt_in"] = profile.get("notifications_opt_in", "true") == "true"
                state.consent["whatsapp_opt_in"] = profile.get("whatsapp_opt_in", "true") == "true"
            for ev in events:
                self.state_mgr.update(uid, ev)

    def save_outputs(self, out_dir: str):
        """Save all replay outputs."""
        os.makedirs(out_dir, exist_ok=True)
        # decisions.jsonl
        with open(os.path.join(out_dir, "decisions.jsonl"), "w", encoding="utf-8") as f:
            for d in self.all_decisions:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        # actions.jsonl
        with open(os.path.join(out_dir, "actions.jsonl"), "w", encoding="utf-8") as f:
            for a in self.all_actions:
                f.write(json.dumps(a, ensure_ascii=False) + "\n")
        # latency_report.json
        self.latency.save(os.path.join(out_dir, "latency_report.json"))
        # viewer states
        vs_dir = os.path.join(out_dir, "viewer_state")
        os.makedirs(vs_dir, exist_ok=True)
        for uid in self.state_mgr.states:
            snap = self.state_mgr.snapshot(uid)
            with open(os.path.join(vs_dir, f"{uid}.json"), "w", encoding="utf-8") as f:
                json.dump(snap, f, indent=2, ensure_ascii=False)
