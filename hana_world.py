"""
hana_world.py
Master pipeline. Called by GitHub Actions 3x/day (morning/midday/evening).

Flow:
  1. Load Hana's persistent state.
  2. Pull real weather/season/daypart for her town.
  3. Pop the oldest pending viewer comment (if any) for her to react to.
  4. Generate today's story continuation (Gemini).
  5. Render each scene as real animation (HuggingFace Wan2.1).
  6. Assemble final captioned 9:16 video with voice + sfx (ffmpeg).
  7. Save the updated state back to hana_state.json.
  8. (Optional) upload to YouTube if credentials are configured.

Run: python hana_world.py --slot morning
If --slot is omitted, the current JST time decides the slot automatically.
"""

import argparse
import datetime
import sys
import traceback
from pathlib import Path

from hana_state import (
    load_state, save_state, start_new_day_if_needed,
    record_video, pop_comment_thread,
)
from japan_data import get_context
import hana_story
import hana_animation
import hana_assembly
import sfx_manager

JST = datetime.timezone(datetime.timedelta(hours=9))


def determine_slot(hour: int) -> str:
    if hour < 11:
        return "morning"
    if hour < 17:
        return "midday"
    return "evening"


def run(slot: str = None) -> Path:
    now = datetime.datetime.now(JST)
    slot = slot or determine_slot(now.hour)
    video_id = f"hana_{now.strftime('%Y%m%d')}_{slot}"

    print(f"[hana_world] Starting run: {video_id}")

    state = load_state()
    state = start_new_day_if_needed(state, now.strftime("%Y-%m-%d"))

    context = get_context(state["location"]["lat"], state["location"]["lon"], now)
    print(f"[hana_world] Weather: {context['weather']['description']}, "
          f"season: {context['season']}, slot: {slot}")

    state, comment = pop_comment_thread(state)
    if comment:
        print(f"[hana_world] Weaving in viewer comment from {comment['from']}: {comment['text'][:80]}")

    print("[hana_world] Generating story...")
    story = hana_story.generate_story(state, context, slot, comment)
    print(f"[hana_world] Title: {story['title']}")

    print(f"[hana_world] Rendering {len(story['scenes'])} scenes...")
    scene_paths = hana_animation.render_all_scenes(story, video_id)

    ambience_path = sfx_manager.ambience_for_season_weather(
        context["season"], context["weather"]["description"]
    )

    print("[hana_world] Assembling final video...")
    final_path = hana_assembly.assemble(story, scene_paths, video_id, ambience_path)
    print(f"[hana_world] Final video: {final_path}")

    state = record_video(
        state,
        slot=slot,
        weather_desc=context["weather"]["description"],
        story_summary=story["narration_summary"],
        emotional_state=story["emotional_state_after"],
        state_updates=story.get("state_updates"),
    )
    save_state(state)
    print("[hana_world] State saved.")

    return final_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", choices=["morning", "midday", "evening"], default=None)
    args = parser.parse_args()

    try:
        final_path = run(args.slot)
        print(f"SUCCESS: {final_path}")
    except Exception:
        print("[hana_world] FAILED:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
