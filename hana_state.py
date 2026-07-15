"""
hana_state.py
Hana's memory. This is the file that makes her a continuous person
instead of a fresh character every video. Read before writing every
story, updated after every video is produced.
"""

import json
import os
from copy import deepcopy

STATE_PATH = os.path.join(os.path.dirname(__file__), "hana_state.json")

MAX_RECENT_EVENTS = 12   # keep the memory window tight so prompts stay cheap
MAX_DAY_LOG = 3          # morning / midday / evening of the current day


def load_state() -> dict:
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    tmp_path = STATE_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, STATE_PATH)  # atomic write, avoids corrupting state on crash


def start_new_day_if_needed(state: dict, today_str: str) -> dict:
    """If this is the first video of a new calendar day, roll the day counter
    and fold yesterday's day_log into recent_events."""
    last_date = state.get("_last_date")
    if last_date != today_str:
        if state.get("day_log_today"):
            summary = " | ".join(state["day_log_today"])
            state["recent_events"].insert(0, f"Day {state['day_count']}: {summary}")
            state["recent_events"] = state["recent_events"][:MAX_RECENT_EVENTS]
        if last_date is not None:
            state["day_count"] += 1
        state["day_log_today"] = []
        state["_last_date"] = today_str
    return state


def record_video(state: dict, slot: str, weather_desc: str, story_summary: str,
                  emotional_state: str, state_updates: dict = None) -> dict:
    """
    Called after a video's story is generated (before or after rendering — doesn't
    matter, this only touches the memory file, not the media).

    slot: 'morning' | 'midday' | 'evening'
    story_summary: one or two sentences, what happened in THIS video
    state_updates: optional dict of partial updates, e.g.
        {
          "garden": {"tomatoes": "sprouted"},
          "ongoing_projects": [{"name": "pottery", "status": "...", "days_in": 6}],
          "kyoto_yen_delta": 500
        }
    """
    state = deepcopy(state)
    state["last_video_slot"] = slot
    state["weather_yesterday"] = weather_desc
    state["emotional_state"] = emotional_state
    state.setdefault("day_log_today", []).append(f"[{slot}] {story_summary}")
    state["day_log_today"] = state["day_log_today"][-MAX_DAY_LOG:]

    if state_updates:
        garden = state_updates.get("garden")
        if garden:
            state["garden"].update(garden)

        landmarks = state_updates.get("landmarks")
        if landmarks:
            state["landmarks"].update(landmarks)

        projects = state_updates.get("ongoing_projects")
        if projects:
            by_name = {p["name"]: p for p in state["ongoing_projects"]}
            for p in projects:
                by_name.setdefault(p["name"], {})
                by_name[p["name"]].update(p)
            state["ongoing_projects"] = list(by_name.values())

        yen_delta = state_updates.get("kyoto_yen_delta")
        if yen_delta:
            for p in state["ongoing_projects"]:
                if p["name"] == "kyoto_savings":
                    p["yen_saved"] = max(0, p.get("yen_saved", 0) + yen_delta)
                    p["status"] = f"{p['yen_saved']} of {p.get('yen_goal', 50000)} yen saved"

    return state


def queue_comment_thread(state: dict, comment_text: str, author_hint: str = "a viewer") -> dict:
    """Stores a viewer comment Hana should react to in her NEXT video."""
    state = deepcopy(state)
    state.setdefault("pending_comment_threads", []).append({
        "text": comment_text,
        "from": author_hint,
    })
    state["pending_comment_threads"] = state["pending_comment_threads"][-5:]
    return state


def pop_comment_thread(state: dict) -> tuple:
    """Pull the oldest pending comment for Hana to respond to this video, if any."""
    state = deepcopy(state)
    threads = state.get("pending_comment_threads", [])
    if not threads:
        return state, None
    thread = threads.pop(0)
    state["pending_comment_threads"] = threads
    return state, thread
