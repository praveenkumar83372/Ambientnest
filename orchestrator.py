"""
C-Suite Executive Orchestrator
Master pipeline runner that executes all agent workflows and triggers production:

1. CAO: Fetches analytics performance report.
2. CEO: Analyzes metrics and sets strategic category/directive.
3. CCO: Generates high-hook 60s script with dynamic news context.
4. CVO: Takes script and builds exact 20-scene storyboard with visual direction.
5. Production Pipeline: Downloads assets, generates neural TTS,
   applies visual effects, mixes multi-track SFX/music, and uploads to YouTube.
"""

import os
import json
import asyncio
from cao_agent import ChiefAnalyticsOfficer
from ceo_agent import ChiefExecutiveOfficer
from cco_agent import ChiefContentOfficer
from cvo_agent import ChiefVisualOfficer

from tts_generator import generate_audio_and_subtitles

# Import visual & asset modules with fallback handling
try:
    from asset_fetcher import download_and_prepare_assets
except ImportError:
    from asset_engine import download_scene_assets as download_and_prepare_assets

from visual_engine import process_all_visual_assets
from video_assembly import download_background_music, assemble_final_video, upload_to_youtube


def run_c_suite_orchestration():
    print("=" * 60)
    print("👔 FACELESS WEALTH C-SUITE EXECUTIVE PIPELINE")
    print("=" * 60)

    # Step 1: Initialize Agents
    cao = ChiefAnalyticsOfficer()
    ceo = ChiefExecutiveOfficer()
    cco = ChiefContentOfficer()
    cvo = ChiefVisualOfficer()

    # Step 2: CAO Performance Briefing
    try:
        cao_briefing = cao.evaluate_channel_performance()
    except Exception as e:
        print(f"⚠️ CAO Briefing fallback: {e}")
        cao_briefing = {}

    # Step 3: CEO Strategy & Directive
    try:
        ceo_directive = ceo.issue_daily_directive(cao_briefing)
        target_category = ceo_directive.get("chosen_category") if isinstance(ceo_directive, dict) else None
    except Exception as e:
        print(f"⚠️ CEO Directive fallback: {e}")
        target_category = None

    # Step 4: CCO Writes Script & SEO Metadata
    script_payload = cco.create_script(category=target_category)

    # Step 5: CVO Builds 20-Scene Storyboard & Visual Direction
    try:
        if hasattr(cvo, "generate_storyboard"):
            storyboard = cvo.generate_storyboard(script_payload)
        elif hasattr(cvo, "direct_visual_storyboard"):
            storyboard = cvo.direct_visual_storyboard(script_payload)
        else:
            storyboard = {"visual_prompts": script_payload.get("visual_prompts", [])}
    except Exception as e:
        print(f"⚠️ CVO Storyboard fallback: {e}")
        storyboard = {"visual_prompts": script_payload.get("visual_prompts", [])}

    # Step 6: Consolidate Output Payload
    final_payload = {
        "topic": script_payload.get("topic", "Financial Secret"),
        "category": script_payload.get("category", target_category),
        "title": script_payload.get("title"),
        "description": script_payload.get("description"),
        "tags": script_payload.get("tags"),
        "narration": script_payload.get("narration"),
        "visual_prompts": storyboard.get("visual_prompts", script_payload.get("visual_prompts", [])),
        "music_mood": storyboard.get("music_mood", "dark ambient cinematic"),
        "sfx_triggers": storyboard.get("sfx_triggers", [0.2, 3.0, 6.0, 9.0])
    }

    with open("current_script.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=4)

    print("\n✅ C-Suite Strategy & Script Generation Complete!")
    print(f"📌 Title: {final_payload['title']}")
    print(f"🎬 Scenes: {len(final_payload['visual_prompts'])} prompts saved to current_script.json")
    return final_payload


async def run_production_pipeline(payload):
    print("\n" + "=" * 60)
    print("⚙️ STARTING VIDEO PRODUCTION ENGINE")
    print("=" * 60)

    narration_text = payload["narration"]
    visual_prompts = payload["visual_prompts"]
    music_mood = payload.get("music_mood", "dark ambient cinematic")

    freesound_key = os.getenv("FREESOUND_API_KEY")

    # 1. Neural Voice & Subtitle Generation (+12% speech rate)
    print("\n🎙️ Generating Neural TTS Voiceover & SRT Subtitles...")
    await generate_audio_and_subtitles(narration_text, audio_out="narration.mp3", srt_out="subtitles.srt")

    # 2. Download Visual Assets
    print("\n📥 Downloading Visual Scene Assets...")
    raw_assets = download_and_prepare_assets(visual_prompts)

    # 3. Format & Standardize Assets (1080x1920 Vertical Clips)
    processed_scene_paths = process_all_visual_assets(raw_assets)

    # 4. Fetch Background Music Track
    bg_music_path = download_background_music(mood=music_mood, freesound_api_key=freesound_key)

    # 5. Format Scene Asset List for Video Assembly
    reformatted_asset_list = []
    for idx, path in enumerate(processed_scene_paths):
        if isinstance(path, dict):
            reformatted_asset_list.append(path)
        else:
            reformatted_asset_list.append({
                "file_path": path,
                "type": "video" if str(path).endswith(".mp4") else "image",
                "target_duration": 3.0,
                "scene_index": idx
            })

    # 6. Assemble Final Master Video (With Watermark & Dual-Color Captions)
    final_video_file = assemble_final_video(
        asset_list=reformatted_asset_list,
        narration_path="narration.mp3",
        srt_path="subtitles.srt",
        music_path=bg_music_path,
        output_path="final_short.mp4"
    )

    # 7. Upload Final MP4 to YouTube Channel
    if os.path.exists(final_video_file):
        print("\n🚀 Triggering YouTube Upload...")
        upload_to_youtube(
            video_path=final_video_file,
            title=payload["title"],
            description=payload["description"],
            tags=payload["tags"]
        )

    print("\n🎉 WEALTH SHORTS AUTOMATION CYCLE COMPLETE!")


if __name__ == "__main__":
    # Execute full C-Suite Orchestration
    script_payload = run_c_suite_orchestration()

    # Execute Production Workflow
    asyncio.run(run_production_pipeline(script_payload))