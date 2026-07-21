"""
Financial Channel State & Intelligence Manager
Tracks channel progress, content category rotation, revenue targets,
and topic history to eliminate content duplication.
"""

import os
import json
import datetime

STATE_FILE = "channel_state.json"

# Core Financial Content Pillars
CATEGORIES = [
    "Dark Psychology & Wealth Secrets",
    "Money Breakdown & Visual Case Studies",
    "The Wealth Rules & Storytelling"
]

DEFAULT_STATE = {
    "channel_name": "Faceless Wealth Intelligence",
    "created_at": datetime.date.today().isoformat(),
    "metrics": {
        "subscribers": 0,
        "estimated_revenue_usd": 0.0,
        "total_videos_published": 0,
        "current_target_usd": 1000.0
    },
    "category_rotation": {
        "last_category_index": -1,
        "category_counts": {cat: 0 for cat in CATEGORIES}
    },
    "history": [],  # List of previously generated video topics
    "last_published_time": None
}


def load_state(path=STATE_FILE):
    """Loads current channel state or creates initial zero-budget state."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
                print(f"📈 Channel State Loaded — Total Videos: {state['metrics']['total_videos_published']}")
                return state
        except Exception as e:
            print(f"⚠️ Error reading state file: {e}. Reinitializing default state.")

    print("🚀 Initializing $0 Budget / 0 Sub Channel State...")
    state = DEFAULT_STATE.copy()
    save_state(state, path)
    return state


def save_state(state, path=STATE_FILE):
    """Saves updated channel state back to JSON."""
    state["last_updated"] = datetime.datetime.utcnow().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
    print(f"💾 Channel state saved successfully.")


def get_next_category(state):
    """
    Selects the next financial content category in strict rotation.
    Returns category name.
    """
    rotation = state.get("category_rotation", {})
    last_index = rotation.get("last_category_index", -1)
    
    next_index = (last_index + 1) % len(CATEGORIES)
    next_category = CATEGORIES[next_index]

    # Update rotation tracking
    state["category_rotation"]["last_category_index"] = next_index
    state["category_rotation"]["category_counts"][next_category] = (
        state["category_rotation"]["category_counts"].get(next_category, 0) + 1
    )
    
    save_state(state)
    return next_category


def log_generated_video(state, topic_title, category):
    """Logs generated topic into history to prevent duplicate concepts in future runs."""
    state["metrics"]["total_videos_published"] += 1
    state["last_published_time"] = datetime.datetime.utcnow().isoformat()

    history_item = {
        "timestamp": datetime.date.today().isoformat(),
        "topic": topic_title,
        "category": category
    }

    state.setdefault("history", []).insert(0, history_item)
    # Keep last 50 video topics in memory for reference
    state["history"] = state["history"][:50]

    save_state(state)


def get_topic_history_summary(state, max_items=10):
    """Returns a list of recently used topics to pass to LLM as anti-repeat context."""
    return [item.get("topic") for item in state.get("history", [])[:max_items]]


def update_channel_metrics(state, subscribers=None, revenue_usd=None):
    """Updates channel metrics as analytics become available."""
    if subscribers is not None:
        state["metrics"]["subscribers"] = subscribers
    if revenue_usd is not None:
        state["metrics"]["estimated_revenue_usd"] = revenue_usd
    save_state(state)


if __name__ == "__main__":
    state = load_state()
    cat = get_next_category(state)
    print(f"Next automated content category: '{cat}'")