"""Event stream processing: loading, deduplication, user indexing."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional


def parse_ts(s: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp string to a datetime object."""
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_events(path: str) -> list[dict]:
    """Load events from a JSONL file, deduplicate by event_id, sort by received_at."""
    events = []
    seen_ids: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            eid = event.get("event_id")
            if eid and eid in seen_ids:
                continue
            if eid:
                seen_ids.add(eid)
            events.append(event)
    events.sort(key=lambda e: e.get("received_at", ""))
    return events


def load_events_with_dups(path: str) -> list[dict]:
    """Load events from a JSONL file WITHOUT deduplication (for testing)."""
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    events.sort(key=lambda e: e.get("received_at", ""))
    return events


def build_user_event_index(events: list[dict]) -> dict[str, list[dict]]:
    """Index events by user_id."""
    index: dict[str, list[dict]] = {}
    for event in events:
        uid = event.get("user_id")
        if uid:
            if uid not in index:
                index[uid] = []
            index[uid].append(event)
    return index


def is_duplicate(event: dict, seen_ids: set[str]) -> bool:
    """Check if an event_id was already processed."""
    eid = event.get("event_id")
    if eid and eid in seen_ids:
        return True
    return False


def compute_event_age(event: dict) -> float:
    """Compute age = received_at - occurred_at in seconds."""
    received = parse_ts(event.get("received_at"))
    occurred = parse_ts(event.get("occurred_at"))
    if received and occurred:
        return (received - occurred).total_seconds()
    return 0.0


def get_event_user_ids(events: list[dict]) -> set[str]:
    """Get all unique user IDs from a list of events."""
    return {e["user_id"] for e in events if "user_id" in e}
