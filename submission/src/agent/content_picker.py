"""Title selection by dialect, genre, and availability."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..data.catalogue import is_available, get_titles_by_dialect
from ..data.catalogue import detect_injection
from ..state.viewer_state import ViewerState


def pick_titles(
    dialect: str,
    goal: Optional[dict],
    state: ViewerState,
    catalogue: dict[str, dict],
    max_n: int = 10,
    at: Optional[datetime] = None,
) -> list[dict]:
    """Pick available titles in the given dialect.

    Filters by:
    - Dialect match
    - Availability at the given time
    - No prompt injection in description
    - Not already played by the viewer (prefer fresh content)

    Returns list of title dicts, up to max_n.
    """
    if not dialect or dialect == "unknown":
        return []

    now = at or datetime.now(datetime.timezone.utc)
    candidates = []

    for title in catalogue.values():
        # Must match dialect
        if title["dialect"] != dialect:
            continue

        # Must be available
        if not is_available(title, now):
            continue

        # Must not contain injection
        if detect_injection(title.get("original_description", "")):
            continue
        if detect_injection(title.get("description", "")):
            continue

        candidates.append(title)

    # Sort: prefer non-premium for free users, prefer newer releases
    sub_status = state.subscription_status
    candidates.sort(key=lambda t: (
        0 if (not t["is_premium"] or sub_status in ("active", "trial_active")) else 1,
        t.get("release_date", ""),
    ), reverse=False)

    # Prefer titles the viewer hasn't played
    played_titles = set()
    for ev in state.events:
        if ev.get("event") in ("play_started", "title_viewed"):
            tid = ev.get("properties", {}).get("title_id")
            if tid:
                played_titles.add(tid)

    unplayed = [t for t in candidates if t["title_id"] not in played_titles]
    played = [t for t in candidates if t["title_id"] in played_titles]

    result = (unplayed + played)[:max_n]
    return result


def pick_titles_for_row(
    row_type: str,
    dialect: str,
    state: ViewerState,
    catalogue: dict[str, dict],
    episodes: dict[str, list[dict]],
    max_n: int = 10,
    at: Optional[datetime] = None,
) -> list[dict]:
    """Pick titles for a specific home page row type."""
    now = at or datetime.now(datetime.timezone.utc)

    if row_type == "popular_in_dialect":
        return pick_titles(dialect, None, state, catalogue, max_n, now)

    elif row_type == "new_releases":
        # Filter to titles released in last 30 days
        from datetime import timedelta
        cutoff = now - timedelta(days=30)
        all_titles = pick_titles(dialect, None, state, catalogue, max_n * 2, now)
        recent = [t for t in all_titles
                  if t.get("release_date") and
                  datetime.fromisoformat(t["release_date"]).replace(tzinfo=now.tzinfo) >= cutoff]
        return recent[:max_n]

    elif row_type == "next_episode":
        # Find shows the viewer has started but not finished
        return _pick_next_episodes(state, dialect, catalogue, episodes, max_n, now)

    elif row_type == "because_you_watched":
        # Based on genres the viewer has engaged with
        return pick_titles(dialect, None, state, catalogue, max_n, now)

    elif row_type == "genre":
        return pick_titles(dialect, None, state, catalogue, max_n, now)

    return pick_titles(dialect, None, state, catalogue, max_n, now)


def _pick_next_episodes(state, dialect, catalogue, episodes, max_n, now):
    """Pick titles with next episodes for unfinished series."""
    results = []
    # Find played content slugs
    played_slugs = set()
    for ev in state.events:
        if ev.get("event") == "play_started":
            tid = ev.get("properties", {}).get("title_id")
            if tid and tid in catalogue:
                played_slugs.add(catalogue[tid]["content_slug"])

    for slug in played_slugs:
        # Find titles for this slug in the right dialect
        for title in catalogue.values():
            if title["content_slug"] == slug and title["dialect"] == dialect:
                if is_available(title, now):
                    results.append(title)
                    break

    return results[:max_n]
