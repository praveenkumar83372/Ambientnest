"""
Financial Visual & Audio Master Engine
Processes stock video clips, static images, natural human voiceover, 
sound effects, background music, and dynamic animated captions.

Standardizes resolution to 1080x1920 (9:16 portrait), applies Ken Burns 
effects, burns in dynamic subtitles, and ensures zero trailing silence.
"""

import os
import shutil as _shutil
from PIL import Image, ImageDraw, ImageFont

# Optional dependency for SRT parsing
try:
    import pysrt
    HAS_PYSRT = True
except ImportError:
    HAS_PYSRT = False

# MoviePy compatibility handler (Supports both MoviePy v1 and v2)
try:
    from moviepy import (
        VideoFileClip, ImageClip, CompositeVideoClip, AudioFileClip, 
        CompositeAudioClip, TextClip, concatenate_videoclips
    )
    MOVIEPY_V2 = True
except ImportError:
    from moviepy.editor import (
        VideoFileClip, ImageClip, CompositeVideoClip, AudioFileClip, 
        CompositeAudioClip, TextClip, concatenate_videoclips
    )
    MOVIEPY_V2 = False


def _find_ffmpeg():
    f = _shutil.which("ffmpeg")
    if f:
        return f
    fallback_paths = [r"C:\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"]
    for p in fallback_paths:
        if os.path.exists(p):
            return p
    return "ffmpeg"


FFMPEG = _find_ffmpeg()


def create_placeholder_image(output_path, text="Financial Secret"):
    """Generates an aesthetic dark-themed financial fallback image if an asset download fails."""
    img = Image.new("RGB", (1080, 1920), color=(15, 23, 42))  # Dark slate background
    draw = ImageDraw.Draw(img)

    draw.rectangle([50, 800, 1030, 1120], fill=(30, 41, 59), outline=(234, 179, 8), width=3)

    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except Exception:
        font = ImageFont.load_default()

    draw.text((540, 960), text, fill=(255, 255, 255), font=font, anchor="mm")
    img.save(output_path)
    return output_path


def apply_ken_burns_effect(image_path, duration=3.0, target_size=(1080, 1920)):
    """
    Applies a smooth dynamic zoom-in (Ken Burns) effect to static photos.
    """
    img_clip = ImageClip(image_path)
    
    # Set duration
    if hasattr(img_clip, "with_duration"):
        img_clip = img_clip.with_duration(duration)
    else:
        img_clip = img_clip.set_duration(duration)

    # Resize to 1920 height
    if hasattr(img_clip, "resized"):
        img_clip = img_clip.resized(height=target_size[1])
        if img_clip.w < target_size[0]:
            img_clip = img_clip.resized(width=target_size[0])
        
        # Center crop
        img_clip = img_clip.cropped(x_center=img_clip.w / 2, y_center=img_clip.h / 2, width=1080, height=1920)
        
        # Smooth zoom
        zoomed_clip = img_clip.resized(lambda t: 1.0 + 0.05 * t)
        pos_clip = zoomed_clip.with_position("center") if hasattr(zoomed_clip, "with_position") else zoomed_clip.set_position("center")
        final_clip = CompositeVideoClip([pos_clip], size=target_size)
        return final_clip.with_duration(duration) if hasattr(final_clip, "with_duration") else final_clip.set_duration(duration)
    
    else:
        # Legacy MoviePy v1 fallback
        img_clip = img_clip.resize(height=target_size[1])
        if img_clip.w < target_size[0]:
            img_clip = img_clip.resize(width=target_size[0])

        img_clip = img_clip.crop(x_center=img_clip.w / 2, y_center=img_clip.h / 2, width=1080, height=1920)
        zoomed_clip = img_clip.resize(lambda t: 1.0 + 0.05 * t)
        final_clip = CompositeVideoClip([zoomed_clip.set_position("center")], size=target_size)
        return final_clip.set_duration(duration)


def add_dynamic_subtitles(video_clip, srt_path):
    """
    Parses an SRT subtitle file and overlays high-contrast, bold yellow captions on top of the video.
    """
    if not HAS_PYSRT or not os.path.exists(srt_path):
        print("⚠️ Subtitles skipped: pysrt not installed or .srt file not found.")
        return video_clip

    try:
        subs = pysrt.open(srt_path, encoding='utf-8')
        subtitle_clips = [video_clip]

        for sub in subs:
            start_time = (sub.start.hours * 3600) + (sub.start.minutes * 60) + sub.start.seconds + (sub.start.milliseconds / 1000.0)
            end_time = (sub.end.hours * 3600) + (sub.end.minutes * 60) + sub.end.seconds + (sub.end.milliseconds / 1000.0)
            duration = end_time - start_time
            text = sub.text.strip().upper()

            if not text:
                continue

            # Create high-impact yellow text clip
            if MOVIEPY_V2:
                txt_clip = (
                    TextClip(
                        font="Arial-Bold",
                        text=text,
                        font_size=55,
                        color="yellow",
                        stroke_color="black",
                        stroke_width=3,
                        size=(900, None),
                        method="caption"
                    )
                    .with_start(start_time)
                    .with_duration(duration)
                    .with_position(("center", 1250))
                )
            else:
                txt_clip = (
                    TextClip(
                        text,
                        font="Arial-Bold",
                        fontsize=55,
                        color="yellow",
                        stroke_color="black",
                        stroke_width=3,
                        size=(900, None),
                        method="caption"
                    )
                    .set_start(start_time)
                    .set_duration(duration)
                    .set_position(("center", 1250))
                )

            subtitle_clips.append(txt_clip)

        print(f"💬 [Visual Engine] Applied {len(subs)} burned-in subtitle overlays.")
        return CompositeVideoClip(subtitle_clips)

    except Exception as e:
        print(f"⚠️ Error adding subtitles: {e}. Returning raw video.")
        return video_clip


def process_scene_asset(asset_info, output_dir="temp_processed"):
    """
    Processes a single raw visual asset (video clip or photo) into a 
    standardized 1080x1920 vertical clip.
    """
    os.makedirs(output_dir, exist_ok=True)
    raw_path = asset_info["file_path"]
    asset_type = asset_info["type"]
    idx = asset_info["scene_index"]
    target_duration = asset_info.get("target_duration", 3.0)

    output_path = os.path.join(output_dir, f"scene_processed_{idx:02d}.mp4")

    print(f" 🎬 [Visual Engine] Processing Scene {idx+1} ({asset_type.upper()})...")

    try:
        if asset_type == "video" and os.path.exists(raw_path):
            clip = VideoFileClip(raw_path)

            if hasattr(clip, "subclipped"):
                clip = clip.subclipped(0, target_duration) if clip.duration >= target_duration else clip
            elif hasattr(clip, "subclip"):
                clip = clip.subclip(0, target_duration) if clip.duration >= target_duration else clip

            if hasattr(clip, "resized"):
                clip = clip.resized(height=1920)
                if clip.w > 1080:
                    clip = clip.cropped(x_center=clip.w / 2, width=1080)
                elif clip.w < 1080:
                    clip = clip.resized(width=1080)
            else:
                clip = clip.resize(height=1920)
                if clip.w > 1080:
                    clip = clip.crop(x_center=clip.w / 2, width=1080)
                elif clip.w < 1080:
                    clip = clip.resize(width=1080)

            clip.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio=False,
                preset="ultrafast",
                logger=None
            )
            clip.close()

        else:
            if not os.path.exists(raw_path):
                raw_path = create_placeholder_image(f"temp_placeholder_{idx}.jpg")

            clip = apply_ken_burns_effect(raw_path, duration=target_duration)
            clip.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio=False,
                preset="ultrafast",
                logger=None
            )
            clip.close()

        return output_path

    except Exception as e:
        print(f"⚠️ Error processing scene asset {idx}: {e}. Creating fallback scene.")
        fallback_path = create_placeholder_image(f"temp_fallback_{idx}.jpg")
        clip = apply_ken_burns_effect(fallback_path, duration=target_duration)
        clip.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio=False,
            preset="ultrafast",
            logger=None
        )
        clip.close()
        return output_path


def process_all_visual_assets(asset_list):
    """Loops through all downloaded assets and processes them sequentially."""
    print(f"\n🖼️ [Visual Engine] Processing {len(asset_list)} visual scenes into 1080x1920 clips...")
    processed_paths = []

    for asset in asset_list:
        out_path = process_scene_asset(asset)
        processed_paths.append(out_path)

    print("✅ All visual scenes successfully processed and standardized!")
    return processed_paths


def build_final_master_short(processed_video_paths, voice_path, srt_path=None, bgm_path=None, sfx_path=None, output_filename="final_short.mp4"):
    """
    Assembles final video matching EXACT voice audio length (No silent video tail!),
    burns in dynamic yellow subtitles, applies audio mixing (Voice 200%, BGM 40%, SFX 50%), and renders final MP4.
    """
    print("\n🎧 [Master Audio-Visual Engine] Compiling final high-production Short...")

    if not os.path.exists(voice_path):
        raise FileNotFoundError(f"❌ Voice audio file missing: {voice_path}")

    # Load Voice Audio and boost volume to 200%
    voice_audio = AudioFileClip(voice_path)
    if hasattr(voice_audio, "with_volume_scaled"):
        voice_audio = voice_audio.with_volume_scaled(2.0)
    else:
        voice_audio = voice_audio.volumex(2.0)

    target_duration = voice_audio.duration
    print(f"⏱️ Target Video Duration (Paced to Voice): {target_duration:.2f} seconds")

    # Load video clips until they match exact audio duration
    clips = []
    current_time = 0.0

    while current_time < target_duration:
        for v_file in processed_video_paths:
            if current_time >= target_duration:
                break
            
            clip = VideoFileClip(v_file)
            remaining_time = target_duration - current_time

            if clip.duration > remaining_time:
                clip = clip.subclipped(0, remaining_time) if hasattr(clip, "subclipped") else clip.subclip(0, remaining_time)

            clips.append(clip)
            current_time += clip.duration

    # Concatenate visual tracks
    final_video = concatenate_videoclips(clips, method="compose")

    # Apply Burned-in Subtitles if SRT path provided
    if srt_path and os.path.exists(srt_path):
        final_video = add_dynamic_subtitles(final_video, srt_path)

    # Mix Audio Tracks (Voice: 200%, BGM: 40%, SFX: 50%)
    audio_tracks = [voice_audio]

    if bgm_path and os.path.exists(bgm_path):
        bgm = AudioFileClip(bgm_path)
        bgm = bgm.with_volume_scaled(0.4) if hasattr(bgm, "with_volume_scaled") else bgm.volumex(0.4)
        
        if bgm.duration < target_duration:
            bgm = bgm.looped(duration=target_duration) if hasattr(bgm, "looped") else bgm.loop(duration=target_duration)
        else:
            bgm = bgm.subclipped(0, target_duration) if hasattr(bgm, "subclipped") else bgm.subclip(0, target_duration)
        
        audio_tracks.append(bgm)

    if sfx_path and os.path.exists(sfx_path):
        sfx = AudioFileClip(sfx_path)
        sfx = sfx.with_volume_scaled(0.5) if hasattr(sfx, "with_volume_scaled") else sfx.volumex(0.5)
        sfx = sfx.with_start(0.5) if hasattr(sfx, "with_start") else sfx.set_start(0.5)
        audio_tracks.append(sfx)

    # Attach Composite Audio
    final_audio = CompositeAudioClip(audio_tracks)
    final_video = final_video.with_audio(final_audio) if hasattr(final_video, "with_audio") else final_video.set_audio(final_audio)

    # Write final video file
    print("🚀 Rendering master 1080x1920 Short with balanced audio and subtitles...")
    final_video.write_videofile(
        output_filename,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        logger=None
    )

    # Clean up memory
    final_video.close()
    for c in clips:
        c.close()

    print(f"🎉 MASTER SHORT COMPILED SUCCESSFULLY: {output_filename}")
    return output_filename