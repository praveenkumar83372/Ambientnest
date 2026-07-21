"""
Financial Short Assembly Engine & YouTube Uploader
Combines visual clips, narration, background music, and dynamic SRT captions 
into a final 1080x1920 MP4 file paced strictly to voice length, then posts to YouTube.
"""

import os
import base64
import pickle
import requests
import shutil as _shutil
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Optional dependency for SRT parsing
try:
    import pysrt
    HAS_PYSRT = True
except ImportError:
    HAS_PYSRT = False

# MoviePy compatibility handler
try:
    from moviepy import (
        VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, 
        CompositeAudioClip, concatenate_videoclips, TextClip
    )
    MOVIEPY_V2 = True
except ImportError:
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, 
        CompositeAudioClip, concatenate_videoclips, TextClip
    )
    MOVIEPY_V2 = False


def add_dynamic_subtitles(video_clip, srt_path):
    """Parses .srt file and overlays high-impact yellow text captions on top of the video."""
    if not HAS_PYSRT or not os.path.exists(srt_path):
        print("⚠️ Subtitles skipped: pysrt not installed or .srt file missing.")
        return video_clip

    try:
        subs = pysrt.open(srt_path, encoding='utf-8')
        subtitle_clips = [video_clip]

        for sub in subs:
            start_time = (sub.start.hours * 3600) + (sub.start.minutes * 60) + sub.start.seconds + (sub.start.milliseconds / 1000.0)
            end_time = (sub.end.hours * 3600) + (sub.end.minutes * 60) + sub.end.seconds + (sub.end.milliseconds / 1000.0)
            duration = max(0.2, end_time - start_time)
            text = sub.text.strip().upper()

            if not text:
                continue

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

        print(f"💬 [Video Assembly] Burned in {len(subs)} caption overlays onto video.")
        return CompositeVideoClip(subtitle_clips)

    except Exception as e:
        print(f"⚠️ Subtitle overlay error: {e}. Skipping captions.")
        return video_clip


def assemble_final_video(asset_list, narration_path="narration.mp3", srt_path="subtitles.srt", music_path=None, output_path="final_short.mp4"):
    """
    Assembles final video paced strictly to narration audio length with 200% voice boost, 
    40% BGM, and burned-in SRT captions.
    """
    print("\n🎬 [Video Assembly] Starting master video compilation...")

    if not os.path.exists(narration_path):
        raise FileNotFoundError(f"❌ Narration audio file not found: {narration_path}")

    # Load Narration Audio and boost to 200%
    narration_audio = AudioFileClip(narration_path)
    if hasattr(narration_audio, "with_volume_scaled"):
        narration_audio = narration_audio.with_volume_scaled(2.0)
    else:
        narration_audio = narration_audio.volumex(2.0)

    target_duration = narration_audio.duration
    print(f"⏱️ Video Duration target (Synced to Voice): {target_duration:.2f} seconds")

    # Load visual clips up to exact target_duration
    processed_clips = []
    current_time = 0.0

    while current_time < target_duration:
        for asset in asset_list:
            if current_time >= target_duration:
                break

            file_path = asset["file_path"]
            asset_type = asset["type"]
            remaining_time = target_duration - current_time

            if asset_type == "video" and os.path.exists(file_path):
                clip = VideoFileClip(file_path)
                clip_dur = min(clip.duration, 3.0, remaining_time)
                clip = clip.subclipped(0, clip_dur) if hasattr(clip, "subclipped") else clip.subclip(0, clip_dur)
            else:
                clip = ImageClip(file_path)
                clip_dur = min(3.0, remaining_time)
                clip = clip.with_duration(clip_dur) if hasattr(clip, "with_duration") else clip.set_duration(clip_dur)

            # Resizing to 1080x1920 portrait
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

            processed_clips.append(clip)
            current_time += clip.duration

    base_video = concatenate_videoclips(processed_clips, method="compose")

    # Apply Subtitles Overlay
    if srt_path and os.path.exists(srt_path):
        base_video = add_dynamic_subtitles(base_video, srt_path)

    # Audio Mixing: Voice (200%), BGM (40%)
    audio_tracks = [narration_audio]

    if music_path and os.path.exists(music_path):
        bg_audio = AudioFileClip(music_path)
        bg_audio = bg_audio.with_volume_scaled(0.4) if hasattr(bg_audio, "with_volume_scaled") else bg_audio.volumex(0.4)
        
        if bg_audio.duration < target_duration:
            bg_audio = bg_audio.looped(duration=target_duration) if hasattr(bg_audio, "looped") else bg_audio.loop(duration=target_duration)
        else:
            bg_audio = bg_audio.subclipped(0, target_duration) if hasattr(bg_audio, "subclipped") else bg_audio.subclip(0, target_duration)
        
        audio_tracks.append(bg_audio)

    final_audio = CompositeAudioClip(audio_tracks)
    
    # FIX: Correct variable reference from base_video instead of final_video
    base_video = base_video.with_audio(final_audio) if hasattr(base_video, "with_audio") else base_video.set_audio(final_audio)

    base_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="fast",
        logger=None
    )

    base_video.close()
    for c in processed_clips:
        c.close()

    print(f"✅ Master Short compiled successfully: {output_path}")
    return output_path


def get_authenticated_youtube_service():
    """Retrieves authenticated Google YouTube client using token.pickle or TOKEN_PICKLE_B64 env secret."""
    token_file = "token.pickle"
    
    if not os.path.exists(token_file):
        token_b64 = os.getenv("TOKEN_PICKLE_B64")
        if token_b64:
            print("🔑 Decoding TOKEN_PICKLE_B64 from repository secret...")
            with open(token_file, "wb") as f:
                f.write(base64.b64decode(token_b64))

    if not os.path.exists(token_file):
        print("⚠️ No valid token.pickle found or decoded. Cannot authenticate YouTube API.")
        return None

    try:
        with open(token_file, "rb") as f:
            creds = pickle.load(f)
        return build("youtube", "v3", credentials=creds)
    except Exception as e:
        print(f"❌ Error loading YouTube credentials: {e}")
        return None


def upload_to_youtube(video_path, title, description, tags, publish_at=None):
    """Uploads compiled video to YouTube with complete SEO metadata."""
    youtube = get_authenticated_youtube_service()
    if not youtube:
        print("⚠️ Skipping YouTube upload due to missing authentication.")
        return None

    try:
        if isinstance(tags, list):
            if "ambientnest" not in tags:
                tags.insert(0, "ambientnest")
            if "ambientnest wealth" not in tags:
                tags.insert(1, "ambientnest wealth")
            if "ambientnest shorts" not in tags:
                tags.insert(2, "ambientnest shorts")
        else:
            tags = ["ambientnest", "ambientnest wealth", "wealth", "finance", "shorts"]

        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags[:20],
                "categoryId": "27"  # Education / Business & Finance
            },
            "status": {
                "privacyStatus": "private" if publish_at else "public",
                "selfDeclaredMadeForKids": False
            }
        }

        if publish_at:
            body["status"]["publishAt"] = publish_at

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        print(f"🚀 Uploading to YouTube: '{title}'...")
        response = request.execute()
        video_id = response.get("id")
        print(f"🎉 Upload successful! Video ID: {video_id}")
        return video_id

    except Exception as e:
        print(f"❌ YouTube upload failed: {e}")
        return None