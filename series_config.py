"""
AmbientNest HQ — Series Configuration
5 series, each with unique identity, voice, visuals, and posting day.
"""

import datetime

SERIES = {
    1: {
        "name": "I Was There",
        "tagline": "True testimonies from history's most defining moments",
        "day": "Monday",
        "cron_day": 1,  # 0=Sunday, 1=Monday...
        "hook_template": "My name is {witness}. I was {age} years old. And I was there.",
        "voice": "en-GB-RyanNeural",
        "voice_rate": "-5%",
        "visual_filter": "cinematic_sepia",
        "music_mood": "melancholic orchestral historical",
        "image_style": "vintage historical photograph, sepia tones, aged paper texture, 1900s documentary aesthetic, period accurate, highly detailed",
        "color_grade": "sepia",
        "categories": ["history", "world war", "ancient civilizations", "historical disasters", "famous events"],
        "thumbnail_style": "vintage_retro",
        "episode_prefix": "EP",
    },
    2: {
        "name": "They Never Found Me",
        "tagline": "First-person accounts from history's most baffling disappearances",
        "day": "Tuesday",
        "cron_day": 2,
        "hook_template": "They searched for {days} days. They never found me. This is what really happened.",
        "voice": "en-US-JennyNeural",
        "voice_rate": "-8%",
        "visual_filter": "dark_cold",
        "music_mood": "dark mysterious suspenseful ambient",
        "image_style": "dark moody photography, cold blue tones, mysterious shadows, noir aesthetic, eerie atmosphere, cinematic mystery",
        "color_grade": "cyberpunk",
        "categories": ["mysterious disappearances", "unsolved cases", "lost expeditions", "vanished people", "cold cases"],
        "thumbnail_style": "mystery_hook",
        "episode_prefix": "CASE",
    },
    3: {
        "name": "Last Night on Earth",
        "tagline": "The final hours before history's most terrifying events",
        "day": "Wednesday",
        "cron_day": 3,
        "hook_template": "Nobody knew it would be the last night. Until it was.",
        "voice": "en-US-GuyNeural",
        "voice_rate": "-3%",
        "visual_filter": "horror_red",
        "music_mood": "horror ambient dark tense eerie",
        "image_style": "dark horror photography, ominous red and black tones, unsettling shadows, cinematic horror aesthetic, deeply atmospheric",
        "color_grade": "horror",
        "categories": ["paranormal events", "unexplained phenomena", "historical disasters", "horror history", "survival stories"],
        "thumbnail_style": "bold_dark",
        "episode_prefix": "NIGHT",
    },
    4: {
        "name": "The Secret They Kept",
        "tagline": "Declassified. Buried. Now told for the first time.",
        "day": "Thursday",
        "cron_day": 4,
        "hook_template": "This was classified for {years} years. Now you can know the truth.",
        "voice": "en-US-EricNeural",
        "voice_rate": "+0%",
        "visual_filter": "dark_finance",
        "music_mood": "tense thriller cinematic conspiracy",
        "image_style": "classified document aesthetic, high contrast black and white photography, conspiracy thriller style, government document texture, declassified stamp aesthetic",
        "color_grade": "dark_finance",
        "categories": ["government secrets", "corporate cover-ups", "declassified files", "hidden history", "conspiracies proven true"],
        "thumbnail_style": "breaking_news",
        "episode_prefix": "FILE",
    },
    5: {
        "name": "Born in the Wrong Century",
        "tagline": "The visionaries the world wasn't ready for",
        "day": "Friday",
        "cron_day": 5,
        "hook_template": "They called {name} mad. They called {name} dangerous. History called {name} right.",
        "voice": "en-US-AriaNeural",
        "voice_rate": "-5%",
        "visual_filter": "warm_vivid",
        "music_mood": "inspiring warm cinematic emotional",
        "image_style": "painterly portrait style, warm golden renaissance lighting, timeless artistic aesthetic, museum quality portrait, emotional depth",
        "color_grade": "warm_vivid",
        "categories": ["ahead of their time", "forgotten geniuses", "visionaries", "inventors", "philosophers", "artists"],
        "thumbnail_style": "cinematic_bars",
        "episode_prefix": "STORY",
    },
}

# Day number (weekday) → series number
DAY_TO_SERIES = {s["cron_day"]: num for num, s in SERIES.items()}


def get_todays_series():
    """Return today's series config based on current weekday."""
    weekday = datetime.datetime.utcnow().isoweekday()  # 1=Mon, 7=Sun
    series_num = DAY_TO_SERIES.get(weekday)
    if series_num is None:
        print(f"⚠️ No series scheduled for today (weekday {weekday}). Using Series 1.")
        series_num = 1
    series = SERIES[series_num].copy()
    series["number"] = series_num
    print(f"📺 Today's series: {series['name']} (Series {series_num})")
    return series