"""
C-Suite Executive Orchestrator
Master pipeline runner that executes all agent workflows and triggers production:

1. CAO: Fetches analytics performance report.
2. CEO: Analyzes metrics and sets strategic category/directive.
3. CCO: Pitches fresh concepts, gets CEO approval, writes high-hook 60s script.
4. CVO: Takes script and builds exact 20-scene storyboard with audio direction.
5. Production Pipeline: Downloads assets (0 duplicates), generates neural TTS,
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
from asset_fetcher import download_and_prepare_assets
from sfx_manager import get_sfx_for_scene, mix_sfx_into_scene
from visual_engine import process_all_visual_assets
from video_assembly import download_background_music, assemble_final_video, upload_to_youtube


def run_c_suite_orchestration():
    print("=" * 60)
    print("👔 FACLELESS WEALTH C-SUITE EXECUTIVE PIPELINE")
    print("=" * 60)

    # Step 1: Initialize Agents
    cao = ChiefAnalyticsOfficer()
    ceo = ChiefExecutiveOfficer()
    cco = ChiefContentOfficer()
    cvo = ChiefVisualOfficer()

    # Step 2: CAO Briefing
    cao_briefing = cao.generate_ceo_briefing()

    # Step 3: CCO Concept Pitch & CEO Review Loop
    cco_pitch = cco.pitch_concept_to_ceo(state={})
    ceo_evaluation = ceo.evaluate_cco_pitch(cco_pitch, cao_briefing)

    if ceo_evaluation.get("approved"):
        target_category = ceo_evaluation.get("adjusted_category") or cco_pitch.get("target_category")
        custom_directive = cco_pitch.get("proposed_topic")
    else:
        ceo_directive = ceo.issue_daily_directive(cao_briefing)
        target_category = ceo_directive.get("chosen_category")
        custom_directive = None

    # Step 4: CCO Writes Script & SEO Metadata
    script_payload = cco.create_script(category=target_category, custom_directive=custom_directive)

    # Step 5: CVO Builds 20-Scene Storyboard & Audio Direction
    storyboard = cvo.generate_storyboard(script_payload)

    # Step 6: Consolidate Output Payload
    final_payload = {
        "topic": script_payload.get("topic"),
        "category": target_category,
        "title": script_payload.get("title"),
        "description": script_payload.get("description"),
        "tags": script_payload.get("tags"),
        "narration": script_payload.get("narration"),
        "visual_prompts": storyboard.get("visual_prompts"),
        "music_mood": storyboard.get("music_mood"),
        "sfx_triggers": storyboard.get("sfx_triggers")
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
    sfx_triggers = payload.get("sfx_triggers", [])

    freesound_key = os.getenv("FREESOUND_API_KEY")

    # 1. Neural Voice & Subtitle Generation
    print("\n🎙️ Generating Neural TTS Voiceover & SRT Subtitles...")
    await generate_audio_and_subtitles(narration_text, audio_out="narration.mp3", srt_out="subtitles.srt")

    # 2. Download Pexels Visual Assets (0 Duplicates)
    raw_assets = download_and_prepare_assets(visual_prompts)

    # 3. Format & Standardize Assets (1080x1920, 3.0s, Ken Burns)
    processed_scene_paths = process_all_visual_assets(raw_assets)

    # 4. Fetch & Mix Audio / Sound Effects
    bg_music_path = download_background_music(mood=music_mood, freesound_api_key=freesound_key)

    # 5. Assemble Final Video with MoviePy
    reformatted_asset_list = []
    for idx, path in enumerate(processed_scene_paths):
        reformatted_asset_list.append({
            "file_path": path,
            "type": "video",
            "target_duration": 3.0
        })

    final_video_file = assemble_final_video(
        asset_list=reformatted_asset_list,
        narration_path="narration.mp3",
        srt_path="subtitles.srt",
        music_path=bg_music_path,
        output_path="final_short.mp4"
    )

    # 6. Upload Final MP4 to YouTube Channel
    if os.path.exists(final_video_file):
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