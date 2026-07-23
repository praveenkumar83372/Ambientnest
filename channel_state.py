"""
Channel State Management Module
Tracks topic history, agent deliberations, and enforces high-RPM category rotation
including Billionaire Case Studies and 'Save vs. Don't Save' financial comparisons.
"""

import json
import os

STATE_FILE = "channel_state.json"

# Expanded High-RPM Financial Topic Rotation
CATEGORIES = [
    "Wealth Psychology & Dark Banking Secrets",
    "Billionaire & Trillionaire Lessons (Buffett, Musk, Rockefeller)",
    "Save vs. Don't Save Experiments (Compound Interest & Asset Math)",
    "Credit Cards, Debt Hacking & Tax Avoidance Secrets",
    "Macroeconomics, Inflation Shields & Real Estate",
    "Crypto, AI Tech & Digital Wealth Creation",
    "Frugal Millionaires & Practical Money Habits"
]


def load_state():
    """Loads channel state from JSON file or initializes default state."""
    if not os.path.exists(STATE_FILE):
        return {
            "total_videos": 0,
            "category_index": 0,
            "topic_history": [],
            "agent_deliberations": []
        }
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Warning loading state: {e}. Returning fallback defaults.")
        return {
            "total_videos": 0,
            "category_index": 0,
            "topic_history": [],
            "agent_deliberations": []
        }


def save_state(state):
    """Saves updated state back to channel_state.json."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)
        print("💾 Channel state saved successfully.")
    except Exception as e:
        print(f"❌ Failed to save state: {e}")


def get_next_category(state):
    """Gets the next strategy category in sequence to ensure content variety."""
    idx = state.get("category_index", 0)
    category = CATEGORIES[idx % len(CATEGORIES)]
    state["category_index"] = (idx + 1) % len(CATEGORIES)
    save_state(state)
    return category


def log_generated_video(state, topic, category):
    """Records generated topic and updates channel video history."""
    state["total_videos"] = state.get("total_videos", 0) + 1
    
    history = state.get("topic_history", [])
    history.append({
        "video_number": state["total_videos"],
        "topic": topic,
        "category": category
    })
    
    # Keep last 25 topics in history to avoid repetition
    state["topic_history"] = history[-25:]
    save_state(state)


def get_topic_history_summary(state, max_items=10):
    """Returns recent topics list for LLM context to prevent repeating subjects."""
    history = state.get("topic_history", [])
    return [item.get("topic", "") for item in history[-max_items:]]