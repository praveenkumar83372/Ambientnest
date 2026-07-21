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


def download_background_music(mood="dark ambient", output_path="bg_music.mp3", freesound_api_key=None):
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


def assemble_final_video(asset_list, narration_path="narration.mp3", srt_path="subtitles.srt", music_path=None, output_path="final_short.mp4"):
    print("\n🎬 [Video Assembly] Starting video composition with MoviePy...")
    processed_clips = []

    for asset in asset_list:
        file_path = asset["file_path"]
        asset_type = asset["type"]

        if asset_type == "video" and os.path.exists(file_path):
            clip = VideoFileClip(file_path)
            if hasattr(clip, "subclipped"):
                clip = clip.subclipped(0, 3.0) if clip.duration > 3.0 else clip
            elif hasattr(clip, "subclip"):
                clip = clip.subclip(0, 3.0) if clip.duration > 3.0 else clip
        else:
            clip = ImageClip(file_path)
            clip = clip.with_duration(3.0) if hasattr(clip, "with_duration") else clip.set_duration(3.0)

        # Standardize vertical
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

    base_video = concatenate_videoclips(processed_clips, method="compose")

    audio_tracks = []
    if os.path.exists(narration_path):
        narration_audio = AudioFileClip(narration_path)
        audio_tracks.append(narration_audio)

    if music_path and os.path.exists(music_path):
        bg_audio = AudioFileClip(music_path)
        bg_audio = bg_audio.with_volume(0.15) if hasattr(bg_audio, "with_volume") else bg_audio.volumex(0.15)
        bg_audio = bg_audio.with_duration(base_video.duration) if hasattr(bg_audio, "with_duration") else bg_audio.set_duration(base_video.duration)
        audio_tracks.append(bg_audio)

    if audio_tracks:
        final_audio = CompositeAudioClip(audio_tracks)
        base_video = base_video.with_audio(final_audio) if hasattr(base_video, "with_audio") else base_video.set_audio(final_audio)

    base_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="fast"
    )
    print(f"✅ Video compiled successfully: {output_path}")
    return output_path


def upload_to_youtube(video_path, title, description, tags, publish_at=None):
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
                "categoryId": "27"
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