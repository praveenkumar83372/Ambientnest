"""
Financial Short Assembly Engine & YouTube Uploader
Combines 20 visual clips (3s each), narration, SFX, background music,
and dynamic SRT captions into a final 60s 1080x1920 MP4 file, then posts to YouTube.
"""

import os
import json
import pickle
import requests
import subprocess
import shutil as _shutil
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy v1 vs v2 compatibility handler
try:
    from moviepy import (
        VideoFileClip,
        AudioFileClip,
        ImageClip,
        CompositeVideoClip,
        CompositeAudioClip,
        concatenate_videoclips,
        TextClip
    )
except ImportError:
    from moviepy.editor import (
        VideoFileClip,
        AudioFileClip,
        ImageClip,
        CompositeVideoClip,
        CompositeAudioClip,
        concatenate_videoclips,
        TextClip
    )

try:
    from moviepy.video.tools.subtitles import SubtitlesClip
except ImportError:
    SubtitlesClip = None


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


# --- 1. Background Music Fetcher ---
def download_background_music(mood="dark ambient", output_path="bg_music.mp3", freesound_api_key=None):
    """Downloads a background music track based on the mood context."""
    if not freesound_api_key:
        print("⚠️ FREESOUND_API_KEY missing. Skipping background music download.")
        return None

    query = f"financial dark ambient cinematic {mood}"
    url = (
        f"https://freesound.org/apiv2/search/text/"
        f"?query={requests.utils.quote(query)}"
        f"&fields=id,name,previews,duration"
        f"&token={freesound_api_key}&page_size=5"
    )

    try:
        res = requests.get(url, timeout=20).json()
        results = [r for r in (res.get("results") or []) if r.get("duration", 0) >= 30]
        if results:
            track = results[0]
            preview_url = track["previews"].get("preview-hq-mp3") or track["previews"].get("preview-lq-mp3")
            if preview_url:
                audio_data = requests.get(preview_url, timeout=20).content
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                print(f"🎵 Downloaded Background Music: {track['name']}")
                return output_path
    except Exception as e:
        print(f"⚠️ Background music fetch failed: {e}")
    return None


# --- 2. MoviePy Video Compilation ---
def assemble_final_video(asset_list, narration_path="narration.mp3", srt_path="subtitles.srt", music_path=None, output_path="final_short.mp4"):
    """
    Stitches 20 scene assets into a 60s vertical video, overlays narration,
    background music, sound effects, and subtitles.
    """
    print("\n🎬 [Video Assembly] Starting video composition with MoviePy...")
    processed_clips = []

    # Process 20 assets into 1080x1920 3-second clips
    for asset in asset_list:
        file_path = asset["file_path"]
        asset_type = asset["type"]

        if asset_type == "video" and os.path.exists(file_path):
            clip = VideoFileClip(file_path)
            if clip.duration > 3.0:
                clip = clip.subclip(0, 3.0)
            elif clip.duration < 3.0:
                clip = clip.loop(duration=3.0)
        else:
            clip = ImageClip(file_path).set_duration(3.0)

        # Scale/Crop to 9:16 vertical format (1080x1920)
        clip = clip.resize(height=1920)
        if clip.w > 1080:
            clip = clip.crop(x_center=clip.w / 2, width=1080)
        elif clip.w < 1080:
            clip = clip.resize(width=1080)

        processed_clips.append(clip)

    base_video = concatenate_videoclips(processed_clips, method="compose")

    # Audio Mixing setup
    audio_tracks = []

    # Narration Track
    if os.path.exists(narration_path):
        narration_audio = AudioFileClip(narration_path)
        audio_tracks.append(narration_audio)

    # Background Music Track (at 15% volume so narration is dominant)
    if music_path and os.path.exists(music_path):
        bg_audio = AudioFileClip(music_path).volumex(0.15)
        bg_audio = bg_audio.set_duration(base_video.duration)
        audio_tracks.append(bg_audio)

    if audio_tracks:
        final_audio = CompositeAudioClip(audio_tracks)
        base_video = base_video.set_audio(final_audio)

    # Subtitle Generator Overlay
    if os.path.exists(srt_path) and SubtitlesClip is not None:
        try:
            generator = lambda txt: TextClip(
                txt,
                font="Arial-Bold",
                fontsize=52,
                color="yellow",
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(950, None)
            )
            subtitles = SubtitlesClip(srt_path, generator)
            subtitles = subtitles.set_position(("center", 1400))
            final_video = CompositeVideoClip([base_video, subtitles])
        except Exception as e:
            print(f"⚠️ Subtitle rendering warning (continuing without subs): {e}")
            final_video = base_video
    else:
        final_video = base_video

    # Render final video file
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="fast"
    )
    print(f"✅ Video compiled successfully: {output_path}")
    return output_path


# --- 3. YouTube API Uploader ---
def upload_to_youtube(video_path, title, description, tags, publish_at=None):
    """Uploads compiled MP4 video to YouTube channel via Data API v3."""
    token_file = "token.pickle"
    if not os.path.exists(token_file):
        print("⚠️ token.pickle credentials file not found. Skipping YouTube upload.")
        return None

    try:
        with open(token_file, "rb") as f:
            creds = pickle.load(f)

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags,
                "categoryId": "27"  # Category 27 = Education / Finance
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

        print("🚀 Uploading video to YouTube...")
        response = request.execute()
        video_id = response.get("id")
        print(f"🎉 Upload successful! Video ID: {video_id}")
        return video_id

    except Exception as e:
        print(f"❌ YouTube upload failed: {e}")
        return None


if __name__ == "__main__":
    if os.path.exists("current_script.json"):
        with open("current_script.json", "r") as f:
            script_data = json.load(f)

        print(f"Ready to assemble: {script_data.get('title')}")