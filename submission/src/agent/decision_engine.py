"""Core decision engine: decide -> act -> verify loop."""
from __future__ import annotations

import time
from datetime import datetime
from ..config import IST
from ..state.viewer_state import ViewerState
from ..data.loader import DataPack
from ..data.events import parse_ts, compute_event_age
from ..state.fact_resolver import resolve_dialect, resolve_subscription
from .goal_selector import select_goal
from .intervention_builder import choose_intervention
from ..verify.verifier import verify_decision
from ..model.mock_provider import MockModelProvider, ModelError


class DecisionEngine:
    """Core agent loop: decide, act, verify."""

    def __init__(self, pack, model):
        self.pack = pack
        self.model = model
        self._dc = 0  # decision counter
        self._ac = 0  # action counter

    def process_trigger(self, trigger, state, now):
        """Process one trigger. Returns (decision_dict, list_of_action_dicts)."""
        t0 = time.monotonic()
        self._dc += 1
        did = f"D-{self._dc:04d}"
        profile = self.pack.get_profile(state.user_id)
        dialect, d_conflicts = resolve_dialect(state, trigger)
        state.dialect = dialect
        state.dialect_conflicts = d_conflicts
        sub_status, _ = resolve_subscription(state, profile)
        state.subscription_status = sub_status
        received_at = parse_ts(trigger.get("received_at"))
        event_age = compute_event_age(trigger)

        # Holdout: no action
        if state.arm == "holdout":
            return self._no_action(did, state, trigger, "holdout_no_action",
                                   dialect, d_conflicts, received_at, event_age, t0)
        # Select goal
        try:
            goal, g_ev = select_goal(state, self.pack, now, profile)
        except Exception:
            goal, g_ev = None, []
        if not goal:
            return self._no_action(did, state, trigger, g_ev + ["no_eligible_goal"],
                                   dialect, d_conflicts, received_at, event_age, t0)
        state.current_goal = goal
        state.goal_history.append(goal)
        # Model call
        m_ev = []
        try:
            mr = self.model.call(trigger.get("event_id", ""), state.user_id,
                                 {"goal": goal, "dialect": dialect})
            if mr and not mr.get("_malformed"):
                if mr.get("eligible") and mr.get("goal_id"):
                    m_ev.append(f"model:verified-{mr['goal_id']}")
                if "confirmed in billing" in mr.get("reason", ""):
                    m_ev.append("model:unsupported_claim_ignored")
        except (TimeoutError, ModelError, Exception):
            m_ev.append("model:failed_degraded_gracefully")
        # Choose intervention
        atype, adata, conf, i_ev, cids = choose_intervention(goal, state, self.pack, now, dialect)
        all_ev = g_ev + m_ev + i_ev
        assumptions = self._assumptions(state, goal, dialect)
        # Verify
        checks = verify_decision({"goal": goal, "action": atype, "dialect": {"used": dialect}, "content": cids}, state, self.pack, now)
        critical = [f for f in checks["failed"] if f in (
            "holdout_violation", "push_no_consent", "whatsapp_no_consent",
            "quiet_hours_violation", "frequency_cap_exceeded")]
        if critical:
            atype, adata, cids, conf = "none", None, [], 0.0
        elapsed = int((time.monotonic() - t0) * 1000)
        status = "PUBLISHED" if atype != "none" else "NO_ACTION"
        decision = {
            "decision_id": did, "viewer_id": state.user_id,
            "trigger": {"event": trigger.get("event", ""), "received_at": trigger.get("received_at", ""),
                        "event_age_s": round(event_age, 1)},
            "goal": {"id": goal["id"], "deadline": goal["deadline"]} if goal else None,
            "action": atype.upper(), "dialect": {"used": dialect, "source": "app_setting", "conflicts": d_conflicts},
            "content": cids, "confidence": round(conf, 2), "evidence": all_ev[:20],
            "assumptions": assumptions, "checks": checks, "decided_in_ms": elapsed, "status": status,
        }
        actions = []
        if atype != "none" and adata is not None:
            self._ac += 1
            aid = f"A-{self._ac:04d}"
            action = self._build_action(aid, did, state.user_id, trigger, atype, adata, now.isoformat(), dialect)
            actions.append(action)
            state.actions.append(action)
            if atype in ("push", "whatsapp"):
                state.last_message_day = now.astimezone(IST).strftime("%Y-%m-%d")
        state.decisions.append(decision)
        return decision, actions

    def _no_action(self, did, state, trigger, evidence, dialect, conflicts, received_at, event_age, t0):
        elapsed = int((time.monotonic() - t0) * 1000)
        d = {"decision_id": did, "viewer_id": state.user_id,
             "trigger": {"event": trigger.get("event", ""), "received_at": trigger.get("received_at", ""),
                         "event_age_s": round(event_age, 1)},
             "goal": None, "action": "NONE",
             "dialect": {"used": dialect, "source": "app_setting", "conflicts": conflicts},
             "content": [], "confidence": 0.0, "evidence": evidence[:20] if isinstance(evidence, list) else [evidence],
             "assumptions": [], "checks": {"passed": ["no_action"], "failed": []},
             "decided_in_ms": elapsed, "status": "NO_ACTION"}
        state.decisions.append(d)
        return d, []

    def _build_action(self, aid, did, uid, trigger, atype, data, published_at, dialect):
        base = {"action_id": aid, "decision_id": did, "user_id": uid,
                "trigger_event_id": trigger.get("event_id", ""), "type": atype, "published_at": published_at}
        if atype == "home_page":
            base["dialect"] = dialect
            base["hero_title_id"] = data.get("hero_title_id")
            base["rows"] = data.get("rows", [])
        elif atype == "push":
            base["title_id"] = data.get("title_id")
            base["text"] = data.get("text", {})
            base["deeplink"] = data.get("deeplink", "")
            base["send_at"] = data.get("send_at", published_at)
        elif atype == "whatsapp":
            base["template_id"] = data.get("template_id", "")
            base["variables"] = data.get("variables", {})
            base["title_id"] = data.get("title_id", "")
            base["send_at"] = data.get("send_at", published_at)
        elif atype == "in_app_message":
            base["title_id"] = data.get("title_id", "")
            base["text"] = data.get("text", "")
        return base

    def _assumptions(self, state, goal, dialect):
        a = []
        if not state.has_played:
            a.append("viewer has never started a play")
        if not state.has_completed_episode:
            a.append("viewer has never completed an episode")
        if not state.has_purchased:
            a.append("viewer has never purchased")
        if dialect and dialect != "unknown":
            a.append(f"viewer dialect is {dialect}")
        if state.subscription_status:
            a.append(f"subscription status is {state.subscription_status}")
        return a

        return decision, actions
