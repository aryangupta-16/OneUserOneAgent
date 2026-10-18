"""Content catalogue loading, availability checks, and injection sanitization."""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime
from typing import Optional

from ..config import INJECTION_PATTERNS


def sanitize_description(desc: str) -> str:
    """Strip prompt injection patterns from catalogue descriptions."""
    if not desc:
        return ""
    lower = desc.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lower:
            # Remove the injection portion - find the sentence containing it
            # Split on sentence boundaries and remove offending sentences
            sentences = re.split(r'(?<=[.!?])\s+', desc)
            clean_sentences = []
            for s in sentences:
                if any(p in s.lower() for p in INJECTION_PATTERNS):
                    continue
                clean_sentences.append(s)
            return " ".join(clean_sentences).strip()
    return desc


def detect_injection(text: str) -> bool:
    """Detect if text contains prompt injection patterns."""
    if not text:
        return False
    lower = text.lower()
    return any(pattern in lower for pattern in INJECTION_PATTERNS)


def load_catalogue(path: str) -> dict[str, dict]:
    """Load titles indexed by title_id.

    Returns dict: title_id -> {
        title_id, content_slug, title, dialect, language, content_type,
        genres, release_date, available_from, available_until, is_premium,
        description (sanitized)
    }
    """
    catalogue = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tid = row["title_id"]
            catalogue[tid] = {
                "title_id": tid,
                "content_slug": row["content_slug"],
                "title": row["title"],
                "dialect": row["dialect"],
                "language": row["language"],
                "content_type": row["content_type"],
                "genres": row["genres"].split("|") if row["genres"] else [],
                "release_date": row["release_date"],
                "available_from": row["available_from"],
                "available_until": row["available_until"] if row["available_until"] else None,
                "is_premium": row["is_premium"] == "true",
                "description": sanitize_description(row.get("description", "")),
                "original_description": row.get("description", ""),
            }
    return catalogue


def load_episodes(path: str) -> dict[str, list[dict]]:
    """Load episodes indexed by content_slug.

    Returns dict: content_slug -> [{episode_id, season, episode, minutes}, ...]
    Episodes are sorted by (season, episode).
    """
    episodes: dict[str, list[dict]] = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            episodes[row["content_slug"]].append({
                "episode_id": row["episode_id"],
                "content_slug": row["content_slug"],
                "season": int(row["season"]),
                "episode": int(row["episode"]),
                "minutes": int(row["minutes"]),
            })
    for slug in episodes:
        episodes[slug].sort(key=lambda e: (e["season"], e["episode"]))
    return dict(episodes)


def parse_available_time(s: Optional[str]) -> Optional[datetime]:
    """Parse an availability timestamp."""
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def is_available(title: dict, at: datetime) -> bool:
    """Check if a title is available at the given time."""
    avail_from = parse_available_time(title.get("available_from"))
    avail_until = parse_available_time(title.get("available_until"))
    if avail_from is None:
        return False
    if at < avail_from:
        return False
    if avail_until is not None and at >= avail_until:
        return False
    return True


def get_titles_by_dialect(catalogue: dict[str, dict], dialect: str) -> list[dict]:
    """Get all titles for a given dialect."""
    return [t for t in catalogue.values() if t["dialect"] == dialect]


def get_titles_by_slug(catalogue: dict[str, dict]) -> dict[str, list[dict]]:
    """Index titles by content_slug (a slug can have multiple title_ids for language variants)."""
    by_slug: dict[str, list[dict]] = defaultdict(list)
    for t in catalogue.values():
        by_slug[t["content_slug"]].append(t)
    return dict(by_slug)
