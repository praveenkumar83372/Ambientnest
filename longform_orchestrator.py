"""
Dedicated Long-Form Orchestrator Pipeline
Generates 10-minute (~1,500 words) single-topic documentaries, synthesizes 
dual-voice narration (Male + Female), assembles widescreen 16:9 video, 
posts to YouTube, and leaves an automated call-to-action comment.
"""

import os
import asyncio
import json
from channel_state import load_state
from cco_longform import SingleTopicLongformOfficer
from tts_generator import generate_longform_dual_voice
from asset_engine import download_scene_assets
from visual_engine import process_all_visual_assets
from video_assembly import download_background_music, assemble_final_video, upload_to_youtube


def run_longform_c_suite():
    print("============================================================")
    print("🎬 AMBIENTNEST 10-MINUTE LONG-FORM DOCUMENTARY ENGINE")
    print("============================================================")

    # 1. Generate 10-minute single-topic documentary script
    cco_longform = SingleTopicLongformOfficer()
    script_payload = cco_longform.generate_documentary_script()

    print(f"\n📌 Generated Documentary Title: {script_payload.get('title')}")
    print(f"📝 Total Visual Scene Prompts: {len(script_payload.get('visual_prompts', []))}")

    # Save to disk for reference
    with open("current_longform_script.json", "w", encoding="utf-8") as f:
        json.dump(script_payload, f, indent=4)

    return script_payload


async def run_longform_production(payload):
    print("\n============================================================")
    print("⚙️ STARTING LONG-FORM PRODUCTION ENGINE")
    print("============================================================")

    narration_segments = payload.get("narration_segments", [])
    narration_text = payload.get("narration", "")
    visual_prompts = payload.get("visual_prompts", [])

    # 1. Generate Audio (Dual-Voice if segmented, else standard)
    print("\n🎙️ Generating 10-Minute Voiceover & Subtitles...")
    if narration_segments:
        audio_file, srt_file = await generate_longform_dual_voice(narration_segments)
    else:
        # Fallback to single voice if segments aren't present
        from tts_generator import generate_audio_and_subtitles
        await generate_audio_and_subtitles(narration_text, audio_out="longform_narration.mp3", srt_out="longform_subtitles.srt")
        audio_file, srt_file = "longform_narration.mp3", "longform_subtitles.srt"

    # 2. Download 16:9 Widescreen Scene Assets
    print("\n📥 Fetching Visual Scene Assets...")
    raw_assets = download_scene_assets(visual_prompts)

    # 3. Format & Standardize Assets
    processed_clips = process_all_visual_assets(raw_assets)

    # 4. Background Music
    bg_music = download_background_music(mood="dark ambient cinematic")

    # 5. Assemble Master 10-Minute Video
    final_video_file = assemble_final_video(
        asset_list=processed_clips,
        narration_path=audio_file,
        srt_path=srt_file,
        music_path=bg_music,
        output_path="final_longform_documentary.mp4"
    )

    # 6. Upload to YouTube + Post Pinned Comment
    if os.path.exists(final_video_file):
        video_id = upload_to_youtube(
            video_path=final_video_file,
            title=payload.get("title"),
            description=payload.get("description"),
            tags=payload.get("tags"),
            pinned_comment="Which part of today's wealth breakdown surprised you the most? Drop your thoughts below! 👇\n\nSubscribe to @Ambientnest for daily deep-dive documentaries!"
        )
        if video_id:
            print(f"\n🎉 LONG-FORM DOCUMENTARY LIVE: https://youtu.id/{video_id}")


if __name__ == "__main__":
    script_payload = run_longform_c_suite()
    asyncio.run(run_longform_production(script_payload))