"""
Content discovery engine for 5 daily video slots.
Each slot has its own category, voice, visual style, and search strategy.
Slot is auto-detected from UTC hour when main.py runs.
"""

import datetime
from google.genai import types

# ── Slot definitions ─────────────────────────────────────────────────────────
SLOTS = {
    1: {
        "label":    "Finance & Crypto",
        "categories": ["finance", "cryptocurrency", "stock market", "economy", "banking", "investment"],
        "voice":    "christopher",
        "style":    "dark_finance",
        "music":    "tense cinematic dark",
        "real_time": True,
    },
    2: {
        "label":    "AI & Technology",
        "categories": ["artificial intelligence", "technology", "innovation", "robotics", "future tech", "startups"],
        "voice":    "guy",
        "style":    "cyberpunk",
        "music":    "electronic futuristic",
        "real_time": True,
    },
    3: {
        "label":    "Untold History & World Stories",
        "categories": ["world history", "ancient civilizations", "famous scandals", "forgotten empires", "historical mysteries"],
        "voice":    "ryan",
        "style":    "cinematic_sepia",
        "music":    "dramatic orchestral",
        "real_time": False,
    },
    4: {
        "label":    "Science, Space & Nature",
        "categories": ["science discoveries", "space exploration", "nature mysteries", "psychology", "quantum physics", "biology"],
        "voice":    "eric",
        "style":    "vivid_cinematic",
        "music":    "ambient wonder",
        "real_time": True,
    },
    5: {
        "label":    "Travel, Culture & Mind-Blowing Facts",
        "categories": ["travel", "world culture", "psychology facts", "fun facts", "art history", "food culture", "mind blowing"],
        "voice":    "aria",
        "style":    "warm_vivid",
        "music":    "upbeat world",
        "real_time": False,
    },
}

# UTC hour → slot number
HOUR_TO_SLOT = {6: 1, 10: 2, 14: 3, 18: 4, 22: 5}


def detect_slot():
    """Auto-detect which slot to run based on current UTC hour."""
    hour = datetime.datetime.utcnow().hour
    slot = HOUR_TO_SLOT.get(hour)
    if slot is None:
        # Find closest scheduled slot
        closest = min(HOUR_TO_SLOT.keys(), key=lambda h: abs(h - hour))
        slot = HOUR_TO_SLOT[closest]
        print(f"⏰ UTC hour {hour} not on schedule — using nearest slot {slot}")
    else:
        print(f"⏰ UTC hour {hour} → Slot {slot}: {SLOTS[slot]['label']}")
    return slot


def fetch_realtime_news(client, categories):
    """Search for real current news in this slot's categories."""
    category_str = ", ".join(categories[:3])
    print(f"🔎 Searching real-time news: {category_str}...")

    prompt = f"""
    Use Google Search to find the most recent significant and interesting news
    in these areas: {category_str}.

    Search for breaking news, surprising discoveries, viral stories, major events,
    or anything genuinely fascinating that happened recently.

    List 3-6 distinct real stories as factual bullet points with real names,
    numbers, and specific details. If you find nothing substantial, say INSUFFICIENT.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = response.text.strip()
        print(f"📰 News preview: {text[:250]}...")
        return text
    except Exception as e:
        print(f"⚠️ News search failed: {e}")
        return "INSUFFICIENT"


def discover_story_topic(client, categories, exclude_topic=""):
    """
    Discover a fresh, fascinating story/topic in the slot's categories.
    Used when real-time news is thin or slot doesn't use real-time content.
    """
    category_str = ", ".join(categories)
    exclude_line = f"\nDo NOT suggest: {exclude_topic}" if exclude_topic else ""
    print(f"💡 Discovering story topic in: {category_str}...")

    prompt = f"""
    Search the web and find ONE genuinely fascinating, surprising, or little-known
    story, fact, or event related to: {category_str}.{exclude_line}

    It should:
    - Have a real narrative arc or jaw-dropping fact
    - Be the kind of thing that makes people say "I never knew that!"
    - Be specific enough to fill a 5-6 minute video with rich detail
    - Feel fresh — not something every YouTube channel has already covered

    Examples of the TONE and style we want (don't reuse these):
    - The psychologist who discovered humans make decisions 7 seconds before they know it
    - The ancient civilization that invented the internet 2000 years ago using water
    - The tiny island country that accidentally became the world's biggest tax haven
    - The AI that developed its own secret language that no human can read
    - The tribe whose language has no words for numbers and what it reveals about the brain

    Respond with ONLY the topic — one punchy sentence or phrase. No explanation.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        topic = response.text.strip().strip('"').strip("'")
        print(f"💎 Discovered: {topic}")
        return topic
    except Exception as e:
        print(f"⚠️ Topic discovery failed: {e}")
        return f"The most fascinating untold story in {categories[0]}"


def get_slot_content(client, slot_number):
    """
    Main entry point. Returns a dict with everything needed to generate the video:
    raw_news, fallback_topic, news_is_thin, slot config.
    """
    slot = SLOTS[slot_number]
    raw_news = ""
    news_is_thin = True

    if slot["real_time"]:
        raw_news = fetch_realtime_news(client, slot["categories"])
        news_is_thin = (
            "INSUFFICIENT" in raw_news.upper()
            or len(raw_news.strip()) < 250
            or raw_news.strip().count("*") < 2
        )

    fallback_topic = ""
    if news_is_thin:
        fallback_topic = discover_story_topic(client, slot["categories"])

    return {
        "slot": slot_number,
        "label": slot["label"],
        "categories": slot["categories"],
        "voice": slot["voice"],
        "style": slot["style"],
        "music": slot["music"],
        "raw_news": raw_news,
        "news_is_thin": news_is_thin,
        "fallback_topic": fallback_topic,
    }