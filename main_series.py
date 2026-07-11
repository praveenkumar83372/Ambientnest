"""
AmbientNest HQ — Main Series Orchestrator
Detects today's series, generates both Short + Full video, uploads both.
"""

import os
import asyncio
from dotenv import load_dotenv
from google import genai

from series_config import get_todays_series
from episode_engine import generate_episode_scripts
from short_producer import produce_short
from full_producer import produce_full_video

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env")

client = genai.Client(api_key=GEMINI_API_KEY)


def get_episode_number(series_number):
    """Track episode number per series using a simple counter file."""
    counter_file = f".ep_counter_series{series_number}"
    if os.path.exists(counter_file):
        with open(counter_file) as f:
            n = int(f.read().strip()) + 1
    else:
        n = 1
    with open(counter_file, "w") as f:
        f.write(str(n))
    return n


async def run():
    print("=" * 60)
    print("🎬 AmbientNest HQ — Series Episode Generator")
    print("=" * 60)

    # Detect today's series
    series = get_todays_series()
    episode_num = get_episode_number(series["number"])
    print(f"📺 {series['name']} | Episode {episode_num}")
    print(f"🎨 Style: {series['color_grade']} | Voice: {series['voice']}")
    print("=" * 60)

    # Generate scripts for both formats
    scripts = generate_episode_scripts(client, series, episode_num)
    full_script  = scripts["full"]
    short_script = scripts["short"]

    # Produce Short first (faster, tests the pipeline)
    print("\n" + "─"*40)
    print("📱 PHASE 1: Short Teaser")
    print("─"*40)
    short_path, short_id = await produce_short(series, short_script, episode_num)

    # Produce Full video
    print("\n" + "─"*40)
    print("🎬 PHASE 2: Full Episode")
    print("─"*40)
    full_path, full_id = await produce_full_video(series, full_script, episode_num)

    print("\n" + "="*60)
    print(f"✅ {series['name']} Episode {episode_num} — COMPLETE")
    if short_id:
        print(f"📱 Short: https://youtube.com/shorts/{short_id}")
    if full_id:
        print(f"🎬 Full:  https://youtu.be/{full_id}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(run())