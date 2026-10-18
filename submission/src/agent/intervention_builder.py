"""Intervention builder: constructs home_page, push, whatsapp, in_app_message actions."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from ..config import (
    IST, QUIET_HOURS_START, QUIET_HOURS_END,
    MIN_TITLES_PER_ROW, MAX_TITLES_PER_ROW, MAX_HOME_ROWS,
    PUSH_TITLE_MAX_CHARS, PUSH_BODY_MAX_CHARS, FORBIDDEN_PHRASES,
)
from ..state.viewer_state import ViewerState
from ..data.loader import DataPack
from ..data.catalogue import is_available, detect_injection
from .content_picker import pick_titles, pick_titles_for_row


def choose_intervention(goal, state, pack, now, dialect):
    """Choose the best intervention. Returns (type, data, confidence, evidence, content_ids)."""
    if not goal:
        return "none", None, 0.0, ["no_goal_selected"], []
    gid = goal.get("id", "")
    home = build_home_page(state, pack, dialect, goal, now)
    if home:
        cids = _extract_content_ids(home)
        return "home_page", home, 0.6, [f"intervention:home_page-for-{gid}"], cids
    if _can_send_push(state, now):
        push = build_push(state, pack, dialect, goal, now)
        if push:
            return "push", push, 0.5, [f"intervention:push-for-{gid}"], [f"title:{push.get('title_id','')}"]
    if _can_send_whatsapp(state, now):
        wa = build_whatsapp(state, pack, dialect, goal, now)
        if wa:
            return "whatsapp", wa, 0.5, [f"intervention:whatsapp-for-{gid}"], [f"title:{wa.get('title_id','')}"]
    iam = build_in_app_message(state, pack, dialect, goal, now)
    if iam:
        return "in_app_message", iam, 0.4, [f"intervention:in_app-for-{gid}"], []
    return "none", None, 0.0, ["no_valid_intervention"], []


def _can_send_push(state, now):
    return (state.consent.get("notifications_opt_in", False)
            and not _is_quiet_hours(now) and not _already_messaged_today(state, now))

def _can_send_whatsapp(state, now):
    return (state.consent.get("whatsapp_opt_in", False)
            and not _is_quiet_hours(now) and not _already_messaged_today(state, now))

def _is_quiet_hours(dt):
    h = dt.astimezone(IST).hour
    return h >= QUIET_HOURS_START or h < QUIET_HOURS_END

def _already_messaged_today(state, now):
    return state.last_message_day == now.astimezone(IST).strftime("%Y-%m-%d")


def build_home_page(state, pack, dialect, goal, now):
    if not dialect or dialect == "unknown":
        return None
    rows = []
    used_slugs = set()
    for rt in ["popular_in_dialect", "new_releases", "because_you_watched"]:
        if len(rows) >= MAX_HOME_ROWS:
            break
        titles = pick_titles_for_row(rt, dialect, state, pack.catalogue, pack.episodes, MAX_TITLES_PER_ROW, now)
        valid = []
        for t in titles:
            if t["content_slug"] in used_slugs:
                continue
            if not is_available(t, now):
                continue
            if detect_injection(t.get("original_description", "")):
                continue
            valid.append(t)
            used_slugs.add(t["content_slug"])
        if len(valid) >= MIN_TITLES_PER_ROW:
            rows.append({"row_type": rt, "title_ids": [t["title_id"] for t in valid[:MAX_TITLES_PER_ROW]]})
    if not rows:
        return None
    hero_id = rows[0]["title_ids"][0] if rows[0]["title_ids"] else None
    return {"dialect": dialect, "hero_title_id": hero_id, "rows": rows}


def build_push(state, pack, dialect, goal, now):
    titles = pick_titles(dialect, goal, state, pack.catalogue, 3, now)
    if not titles:
        return None
    t = titles[0]
    title_text = t["title"][:PUSH_TITLE_MAX_CHARS]
    body = f"New {t['content_type']} in your language"[:PUSH_BODY_MAX_CHARS]
    for phrase in FORBIDDEN_PHRASES:
        if phrase in body.lower() or phrase in title_text.lower():
            return None
    return {"title_id": t["title_id"], "text": {"title": title_text, "body": body},
            "deeplink": f"ott://title/{t['title_id']}", "send_at": now.isoformat()}


def build_whatsapp(state, pack, dialect, goal, now):
    templates = pack.interventions.get("whatsapp", {}).get("approved_templates", [])
    titles = pick_titles(dialect, goal, state, pack.catalogue, 3, now)
    if not titles or not templates:
        return None
    t = titles[0]
    tmpl = next((tp for tp in templates if tp["template_id"] == "wa_recommend_title_v1"), None)
    if not tmpl:
        return None
    return {"template_id": tmpl["template_id"],
            "variables": {"title_name": t["title"], "dialect_name": dialect},
            "title_id": t["title_id"], "send_at": now.isoformat()}


def build_in_app_message(state, pack, dialect, goal, now):
    titles = pick_titles(dialect, goal, state, pack.catalogue, 3, now)
    if not titles:
        return None
    return {"title_id": titles[0]["title_id"], "text": f"Recommended: {titles[0]['title']}"}


def _extract_content_ids(home_page):
    ids = []
    if home_page.get("hero_title_id"):
        ids.append(f"title:{home_page['hero_title_id']}")
    for row in home_page.get("rows", []):
        for tid in row.get("title_ids", []):
            ref = f"title:{tid}"
            if ref not in ids:
                ids.append(ref)
    return ids

    return state.last_message_day == now.astimezone(IST).strftime("%Y-%m-%d")
