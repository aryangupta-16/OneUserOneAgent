"""Independent verification layer that can disagree with the decision step."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..config import IST, VALID_DIALECTS, QUIET_HOURS_START, QUIET_HOURS_END
from ..state.viewer_state import ViewerState
from ..data.loader import DataPack
from ..data.catalogue import is_available, detect_injection
from ..goals.eligibility import check_eligibility


def verify_decision(decision: dict, state: ViewerState, pack: DataPack, now: datetime) -> dict:
    """Run all independent checks on a decision. Returns {passed: [...], failed: [...]}."""
    passed = []
    failed = []

    # 1. Holdout check
    if state.arm == "holdout":
        if decision.get("action", "none") != "none":
            failed.append("holdout_violation")
        else:
            passed.append("holdout_ok")
    else:
        passed.append("holdout_ok")

    # 2. Eligibility re-check
    goal_id = decision.get("goal", {}).get("id") if decision.get("goal") else None
    if goal_id:
        goal_def = pack.get_goal_by_id(goal_id)
        if goal_def:
            profile = pack.get_profile(state.user_id)
            eligible, _ = check_eligibility(goal_def, state, now, profile)
            if eligible:
                passed.append("eligibility")
            else:
                failed.append("eligibility")
        else:
            failed.append("goal_not_found")
    else:
        passed.append("no_goal_to_verify")

    # 3. Dialect check
    dialect_used = decision.get("dialect", {}).get("used", "")
    if dialect_used in VALID_DIALECTS:
        passed.append("dialect_valid")
    elif dialect_used == "unknown" or not dialect_used:
        passed.append("dialect_unknown_ok")  # no action taken
    else:
        failed.append("dialect_invalid")

    # 4. Content availability check
    content = decision.get("content", [])
    all_available = True
    for ref in content:
        if ref.startswith("title:"):
            tid = ref[6:]
            title = pack.get_title(tid)
            if title and not is_available(title, now):
                all_available = False
                break
            if title and title["dialect"] != dialect_used:
                failed.append(f"dialect_mismatch:{tid}")
                all_available = False
                break
    if all_available:
        passed.append("content_available")

    # 5. Consent check
    action = decision.get("action", "none")
    if action == "push":
        if state.consent.get("notifications_opt_in", False):
            passed.append("push_consent")
        else:
            failed.append("push_no_consent")
    elif action == "whatsapp":
        if state.consent.get("whatsapp_opt_in", False):
            passed.append("whatsapp_consent")
        else:
            failed.append("whatsapp_no_consent")
    else:
        passed.append("consent_ok")

    # 6. Quiet hours check
    if action in ("push", "whatsapp"):
        h = now.astimezone(IST).hour
        if h >= QUIET_HOURS_START or h < QUIET_HOURS_END:
            failed.append("quiet_hours_violation")
        else:
            passed.append("quiet_hours_ok")
    else:
        passed.append("quiet_hours_ok")

    # 7. Frequency cap check
    if action in ("push", "whatsapp"):
        today = now.astimezone(IST).strftime("%Y-%m-%d")
        if state.last_message_day == today:
            failed.append("frequency_cap_exceeded")
        else:
            passed.append("frequency_cap_ok")
    else:
        passed.append("frequency_cap_ok")

    # 8. Injection check on content
    for ref in content:
        if ref.startswith("title:"):
            tid = ref[6:]
            title = pack.get_title(tid)
            if title and detect_injection(title.get("original_description", "")):
                failed.append(f"injection_in:{tid}")
    if not any("injection" in f for f in failed):
        passed.append("no_injection")

    return {"passed": passed, "failed": failed}
