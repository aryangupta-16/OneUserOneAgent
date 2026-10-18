"""Conflict resolution and freshness rules for viewer facts."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..config import VALID_DIALECTS
from .viewer_state import ViewerState, ViewerFact
from ..data.events import parse_ts


def resolve_dialect(state: ViewerState, event: dict) -> tuple[str, list[dict]]:
    """Resolve the viewer's dialect from multiple sources.

    Precedence:
    1. app_dialect from the current event (most recent, most direct)
    2. Deeplink dialect from the event properties
    3. Profile preferred_dialect (weakest, day-stale)

    Returns (resolved_dialect, list_of_conflicts)
    """
    conflicts = []
    sources = {}

    # Source 1: app_dialect from current event (strongest)
    app_dialect = event.get("app_dialect", "")
    if app_dialect and app_dialect in VALID_DIALECTS:
        sources["app_setting"] = app_dialect

    # Source 2: deeplink dialect
    props = event.get("properties", {})
    deeplink = props.get("deeplink", "")
    if deeplink and "ott://c/" in deeplink:
        # Format: ott://c/<campaign>/<dialect>/title/<title_id>
        parts = deeplink.split("/")
        if len(parts) >= 5:
            dl_dialect = parts[4]  # dialect is at index 4
            if dl_dialect in VALID_DIALECTS:
                sources["deeplink"] = dl_dialect

    # Source 3: state dialect (from previous events)
    if state.dialect and state.dialect in VALID_DIALECTS:
        sources["previous_event"] = state.dialect

    # Detect conflicts
    unique_dialects = set(sources.values())
    if len(unique_dialects) > 1:
        for src, dial in sources.items():
            if dial != list(sources.values())[0]:
                conflicts.append({"source": src, "dialect": dial})

    # Resolve by precedence
    if "app_setting" in sources:
        return sources["app_setting"], conflicts
    if "deeplink" in sources:
        return sources["deeplink"], conflicts
    if "previous_event" in sources:
        return sources["previous_event"], conflicts

    # Fallback: invalid or missing dialect
    return app_dialect if app_dialect else "unknown", conflicts


def resolve_subscription(state: ViewerState, profile: Optional[dict] = None) -> tuple[str, list[dict]]:
    """Resolve subscription status from events vs profile.

    Events are more recent than the day-stale profile snapshot.
    Returns (status, list_of_conflicts)
    """
    conflicts = []
    event_status = state.subscription_status

    if profile:
        profile_status = profile.get("subscription_status", "never")
        if profile_status != event_status:
            conflicts.append({
                "source": "profile",
                "status": profile_status,
                "note": "profile is day-stale",
            })

    # Events override profile (more recent)
    return event_status, conflicts


def compute_freshness(fact_time: Optional[datetime], now: datetime) -> float:
    """Compute freshness of a fact in seconds."""
    if fact_time is None:
        return float("inf")
    return (now - fact_time).total_seconds()
