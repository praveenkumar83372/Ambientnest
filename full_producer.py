"""
Produces the full 8-10 minute episode video.
Uses Pexels for footage + series-specific color grade + voice.
Reuses the proven video_engine approach.
"""

import os
import re
import math
import time
import pickle
import subprocess
import requests
import asyncio
import edge_tts
import numpy as np
from dotenv import load_dotenv
from moviepy import (
    VideoFileClip, AudioFileClip,
    concatenate_videoclips, concatenate_audioclips,
    CompositeAudioClip,
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()
PEXELS_API_KEY   = os.environ.get("PEXELS_API_KEY")
FREESOUND_API_KEY = os.environ.get("FREESOUND_API_KEY")
OUTPUT_SIZE = (854, 480)
CLIP_CUT    = 8.0
FPS         = 24


# ── Color grade ───────────────────────────────────────────────────────────────

def _grade_frame(frame, style):
    f = frame.astype(np.float32) / 255.0
    if style == "sepia":
        r = f[:,:,0]*0.393 + f[:,:,1]*0.769 + f[:,:,2]*0.189
        g = f[:,:,0]*0.349 + f[:,:,1]*0.686 + f[:,:,2]*0.168
        b = f[:,:,0]*0.272 + f[:,:,1]*0.534 + f[:,:,2]*0.131
        f = np.clip(np.stack([r*1.1, g, b*0.85], axis=2), 0, 1)
    elif style == "cyberpunk":
        f[:,:,0] = np.clip(f[:,:,0]*0.75, 0, 1)
        f[:,:,1] = np.clip(f[:,:,1]*0.80, 0, 1)
        f[:,:,2] = np.clip(f[:,:,2]*1.35, 0, 1)
        f = np.clip((f-0.5)*1.35+0.5, 0, 1)
    elif style == "horror":
        f = np.clip((f-0.5)*1.4+0.48, 0, 1)
        f[:,:,0] = np.clip(f[:,:,0]*1.25, 0, 1)
        f[:,:,1] = np.clip(f[:,:,1]*0.75, 0, 1)
        f[:,:,2] = np.clip(f[:,:,2]*0.75, 0, 1)
    elif style == "dark_finance":
        f = np.clip((f-0.5)*1.25+0.48, 0, 1)
        f[:,:,2] = np.clip(f[:,:,2]*1.06, 0, 1)
    elif style == "warm_vivid":
        f[:,:,0] = np.clip(f[:,:,0]*1.12, 0, 1)
        gray = (0.299*f[:,:,0]+0.587*f[:,:,1]+0.114*f[:,:,2])[:,:,np.newaxis]
        f = np.clip(gray+(f-gray)*1.3, 0, 1)
    return (np.clip(f, 0, 1)*255).astype(np.uint8)


def _apply_grade(clip, style):
    try:
        return clip.image_transform(lambda frame: _grade_frame(frame, style))
    except Exception:
        try:
            return clip.fl_image(lambda frame: _grade_frame(frame, style))
        except Exception:
            return clip


# ── Audio helpers ─────────────────────────────────────────────────────────────

def _loop_audio(clip, duration):
    if clip.duration >= duration:
        return clip.subclipped(0, duration)
    times = math.ceil(duration / clip.duration)
    return concatenate_audioclips([clip]*times).subclipped(0, duration)


def _scale_vol(clip, factor):
    try:
        from moviepy.audio.fx import MultiplyVolume
        return clip.with_effects([MultiplyVolume(factor)])
    except Exception:
        for m in ("with_volume_scaled", "with_volume_scaling", "volumex"):
            if hasattr(clip, m):
                try: return getattr(clip, m)(factor)
                except: continue
    return clip


# ── Voiceover ─────────────────────────────────────────────────────────────────

async def generate_voiceover(text, path, voice, rate):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(path)


# ── Background music ──────────────────────────────────────────────────────────

def download_music(mood, path):
    if not FREESOUND_API_KEY:
        return
    url = (
        f"https://freesound.org/apiv2/search/text/"
        f"?query={mood}&fields=id,name,previews,duration"
        f"&token={FREESOUND_API_KEY}&page_size=3"
    )
    try:
        res = requests.get(url, timeout=20).json()
        for r in (res.get("results") or []):
            if r.get("duration", 0) > 30:
                audio_url = r["previews"]["preview-hq-mp3"]
                with open(path, "wb") as f:
                    f.write(requests.get(audio_url, timeout=30).content)
                print(f"🎵 Music: {r['name']}")
                return
    except Exception as e:
        print(f"⚠️ Music download failed: {e}")


# ── Pexels footage ────────────────────────────────────────────────────────────

def fetch_clip_urls(keyword, count, headers, used_urls):
    collected = []
    per_page = min(count+6, 15)

    def _search(q, page=1):
        url = (
            f"https://api.pexels.com/videos/search"
            f"?query={q}&per_page={per_page}&page={page}&orientation=landscape"
        )
        try:
            return requests.get(url, headers=headers, timeout=25).json().get("videos") or []
        except:
            return []

    def _best_url(v):
        files = v.get("video_files", [])
        hd = [f for f in files if 1080 <= f.get("height", 0) <= 1440]
        if hd:
            return sorted(hd, key=lambda f: abs(f.get("height",0)-1080))[0]["link"]
        return sorted(files, key=lambda f: f.get("width",9999))[0]["link"] if files else None

    for page in range(1, 4):
        if len(collected) >= count: break
        for v in _search(keyword, page):
            u = _best_url(v)
            if u and u not in used_urls:
                collected.append(u); used_urls.add(u)
            if len(collected) >= count: break

    if len(collected) < count:
        for v in _search(keyword.split()[0]):
            u = _best_url(v)
            if u and u not in used_urls:
                collected.append(u); used_urls.add(u)
            if len(collected) >= count: break

    print(f"    📹 {len(collected)}/{count} clips for '{keyword}'")
    return collected, used_urls


def download_video(url, path, retries=3):
    for attempt in range(retries):
        try:
            data = requests.get(url, timeout=60).content
            with open(path, "wb") as f:
                f.write(data)
            return
        except Exception as e:
            if attempt < retries-1:
                time.sleep(2**attempt)
            else:
                raise e


# ── Upload full video ─────────────────────────────────────────────────────────

def upload_full_video(video_path, title, description, tags, series_name):
    if not os.path.exists("token.pickle"):
        print("❌ token.pickle not found")
        return None
    with open("token.pickle", "rb") as f:
        creds = pickle.load(f)
    youtube = build("youtube", "v3", credentials=creds)

    def clean_tags(tags):
        clean, total = [], 0
        for t in tags:
            t = re.sub(r"[^a-zA-Z0-9 \-]", "", str(t)).strip()
            if not t or len(t) > 30 or total + len(t) > 490:
                continue
            clean.append(t); total += len(t)+1
        return clean or ["AmbientNestHQ", series_name]

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": clean_tags(tags),
            "categoryId": "27",
        },
        "status": {"privacyStatus": "public"},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    try:
        resp = youtube.videos().insert(
            part="snippet,status", body=body, media_body=media
        ).execute()
        vid = resp["id"]
        print(f"✅ Full video live: https://youtu.be/{vid}")
        return vid
    except Exception as e:
        print(f"❌ Full video upload failed: {e}")
        return None


# ── Master full video pipeline ────────────────────────────────────────────────

async def produce_full_video(series, full_script, episode_number):
    print(f"\n🎬 Producing full video for {series['name']} EP{episode_number}...")

    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY not set")

    headers  = {"Authorization": PEXELS_API_KEY}
    used_urls = set()
    final_clips = []
    temp_files  = []
    segments = full_script.get("segments", [])
    voice    = series["voice"]
    rate     = series["voice_rate"]
    style    = series["color_grade"]

    try:
        # Generate all voiceovers first
        print(f"🎙️ Generating {len(segments)} voiceovers...")
        for i, seg in enumerate(segments):
            path = f"f_audio_{i}.mp3"
            temp_files.append(path)
            await generate_voiceover(seg["narration"], path, voice, rate)
            print(f"  🔊 {i+1}/{len(segments)}")

        # Build each segment's video block
        for i, seg in enumerate(segments):
            print(f"\n  ▶ Segment {i+1}/{len(segments)} | '{seg.get('keyword','')}'")
            audio = AudioFileClip(f"f_audio_{i}.mp3")
            audio_dur = audio.duration
            clips_needed = max(2, math.ceil(audio_dur / CLIP_CUT))

            clip_urls, used_urls = fetch_clip_urls(
                seg.get("keyword", "cinematic"), clips_needed, headers, used_urls
            )

            seg_clips = []
            accumulated = 0.0

            for j, vurl in enumerate(clip_urls):
                if accumulated >= audio_dur: break
                cpath = f"f_clip_{i}_{j}.mp4"
                temp_files.append(cpath)
                try:
                    download_video(vurl, cpath)
                    vc = VideoFileClip(cpath).resized(OUTPUT_SIZE)
                    remaining = audio_dur - accumulated
                    cut_dur = min(CLIP_CUT, remaining, vc.duration)
                    if cut_dur <= 0.1: vc.close(); break
                    vc = vc.subclipped(0, cut_dur)
                    seg_clips.append(vc)
                    accumulated += cut_dur
                except Exception as e:
                    print(f"    ⚠️ Clip {j+1} failed: {e}")
                    continue

            if not seg_clips:
                if final_clips:
                    prev = final_clips[-1].without_audio()
                    seg_video = prev.subclipped(0, min(prev.duration, audio_dur)).with_audio(audio)
                    final_clips.append(seg_video)
                    continue
                else:
                    raise RuntimeError(f"No clips for segment {i+1}")

            seg_video = (
                seg_clips[0] if len(seg_clips)==1
                else concatenate_videoclips(seg_clips, method="chain")
            )
            if seg_video.duration > audio_dur:
                seg_video = seg_video.subclipped(0, audio_dur)
            elif seg_video.duration < audio_dur-0.1:
                audio = audio.subclipped(0, seg_video.duration)

            seg_video = seg_video.with_audio(audio)
            final_clips.append(seg_video)
            print(f"    ✅ {seg_video.duration:.1f}s")

        # Concatenate
        print("\n🖥️ Concatenating all segments...")
        full_doc = concatenate_videoclips(final_clips, method="chain")
        total_dur = full_doc.duration
        print(f"   Total: {total_dur/60:.1f} min")

        # Color grade
        print(f"🎨 Applying {style} color grade...")
        full_doc = _apply_grade(full_doc, style)

        # Background music
        music_path = "f_bg_music.mp3"
        temp_files.append(music_path)
        download_music(series["music_mood"], music_path)
        if os.path.exists(music_path):
            bg = AudioFileClip(music_path)
            bg = _loop_audio(bg, total_dur)
            bg = _scale_vol(bg, 0.25)
            if full_doc.audio:
                full_doc = full_doc.with_audio(CompositeAudioClip([full_doc.audio, bg]))

        # Render
        output = f"AmbientNest_EP{episode_number:03d}_{series['name'].replace(' ','_')}.mp4"
        print(f"\n🚀 Rendering {total_dur/60:.1f}-min video...")
        full_doc.write_videofile(
            output, fps=FPS, codec="libx264",
            audio_codec="aac", threads=2, preset="ultrafast", logger=None,
        )

        # Upload
        vid_id = upload_full_video(
            output,
            full_script.get("episode_title", f"{series['name']} EP{episode_number:03d}"),
            full_script.get("description", ""),
            full_script.get("tags", ["AmbientNestHQ"]),
            series["name"],
        )

        return output, vid_id

    finally:
        print("\n🧹 Cleaning up...")
        for p in temp_files:
            if os.path.exists(p):
                try: os.remove(p)
                except: pass