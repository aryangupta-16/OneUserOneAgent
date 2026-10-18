"""Eligibility checking for all 12 goals."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from ..config import IST
from ..state.viewer_state import ViewerState
from ..data.events import parse_ts


def check_eligibility(goal, state, now, profile=None):
    """Check if a viewer is eligible for a goal. Returns (eligible, evidence_refs)."""
    elig = goal.get("eligibility", {})
    gid = goal["goal_id"]
    checks = {
        "G01": _check_g01, "G02": _check_g02, "G03": _check_g03,
        "G04": _check_g04, "G05": _check_g05, "G06": _check_g06,
        "G07": _check_g07, "G08": _check_g08, "G09": _check_g09,
        "G10": _check_g10, "G11": _check_g11, "G12": _check_g12,
    }
    fn = checks.get(gid)
    if fn:
        return fn(elig, state, now, profile)
    return False, []


def _signup(state, profile):
    if state.signup_at:
        return state.signup_at
    if profile and profile.get("signup_at"):
        return parse_ts(profile["signup_at"])
    return None


def _sub(state, profile):
    return state.subscription_status


def _check_g01(elig, state, now, profile):
    signup = _signup(state, profile)
    if not signup or (now - signup).total_seconds() / 86400 > 7 or state.has_played:
        return False, []
    d = (now - signup).total_seconds() / 86400
    return True, [f"goal_rule:G01-signup-{d:.1f}d", "no:play_started"]

def _check_g02(elig, state, now, profile):
    if state.has_completed_episode:
        return False, []
    return True, ["goal_rule:G02-no-episode_completed"]

def _check_g03(elig, state, now, profile):
    signup = _signup(state, profile)
    if not signup or (now - signup).total_seconds() / 86400 > 2:
        return False, []
    d = (now - signup).total_seconds() / 86400
    return True, [f"goal_rule:G03-signup-{d:.1f}d"]

def _check_g04(elig, state, now, profile):
    s = _sub(state, profile)
    if s != "trial_active":
        return False, []
    return True, [f"goal_rule:G04-status-{s}"]

def _check_g05(elig, state, now, profile):
    s = _sub(state, profile)
    if s != "never":
        return False, []
    return True, [f"goal_rule:G05-status-{s}"]

def _check_g06(elig, state, now, profile):
    s = _sub(state, profile)
    if s != "lapsed":
        return False, []
    return True, [f"goal_rule:G06-status-{s}"]

def _check_g07(elig, state, now, profile):
    if not state.has_played or not state.last_play_at:
        return False, []
    d = (now - state.last_play_at).total_seconds() / 86400
    if d < 3:
        return False, []
    return True, [f"goal_rule:G07-idle-{d:.1f}d"]

def _check_g08(elig, state, now, profile):
    s = _sub(state, profile)
    if s != "active":
        return False, []
    return True, [f"goal_rule:G08-status-{s}"]

def _check_g09(elig, state, now, profile):
    s = _sub(state, profile)
    if s != "active":
        return False, []
    cutoff = (now - timedelta(days=14)).astimezone(IST).strftime("%Y-%m-%d")
    recent = {d for d in state.plays_by_day if d >= cutoff}
    if len(recent) > 1:
        return False, []
    return True, [f"goal_rule:G09-{len(recent)}-play-days-in-14d"]

def _check_g10(elig, state, now, profile):
    return True, ["goal_rule:G10-any-user"]

def _check_g11(elig, state, now, profile):
    s = _sub(state, profile)
    if s != "active":
        return False, []
    return True, [f"goal_rule:G11-status-{s}"]

def _check_g12(elig, state, now, profile):
    if not state.last_app_open:
        return True, ["goal_rule:G12-no-app_open"]
    d = (now - state.last_app_open).total_seconds() / 86400
    if d < 14:
        return False, []
    return True, [f"goal_rule:G12-absent-{d:.1f}d"]

    return state.subscription_status
