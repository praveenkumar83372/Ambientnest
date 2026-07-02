"""
Production video assembly engine.
- Multiple unique 6.5s clips per segment, no reuse across whole video
- Color grading per visual style (cyberpunk, sepia, vivid, etc.)
- SFX whoosh at every clip cut (50% volume)
- Background music at 30% volume
- Voice narration at 100% volume
- Audio: concatenate-based looping (stable on all MoviePy 2.x versions)
"""

import os
import math
import time
import requests
import numpy as np
from dotenv import load_dotenv
from moviepy import (
    VideoFileClip, AudioFileClip,
    concatenate_videoclips, concatenate_audioclips,
    CompositeAudioClip,
)

load_dotenv()
FREESOUND_API_KEY = os.environ.get("FREESOUND_API_KEY")
PEXELS_API_KEY   = os.environ.get("PEXELS_API_KEY")

CLIP_CUT_DURATION = 6.5   # seconds per visual cut
TARGET_FPS        = 24
OUTPUT_SIZE       = (1280, 720)


# ── Color grading ─────────────────────────────────────────────────────────────

def _grade_frame(frame, style):
    f = frame.astype(np.float32) / 255.0
    if style == "cyberpunk":
        f[:,:,0] = np.clip(f[:,:,0] * 0.75, 0, 1)
        f[:,:,1] = np.clip(f[:,:,1] * 0.80, 0, 1)
        f[:,:,2] = np.clip(f[:,:,2] * 1.35, 0, 1)
        f = np.clip((f - 0.5) * 1.35 + 0.5, 0, 1)
    elif style == "cinematic_sepia":
        r = f[:,:,0]*0.393 + f[:,:,1]*0.769 + f[:,:,2]*0.189
        g = f[:,:,0]*0.349 + f[:,:,1]*0.686 + f[:,:,2]*0.168
        b = f[:,:,0]*0.272 + f[:,:,1]*0.534 + f[:,:,2]*0.131
        f = np.clip(np.stack([r*1.1, g, b*0.85], axis=2), 0, 1)
    elif style == "vivid_cinematic":
        gray = (0.299*f[:,:,0] + 0.587*f[:,:,1] + 0.114*f[:,:,2])[:,:,np.newaxis]
        f = np.clip(gray + (f - gray) * 1.55, 0, 1)
    elif style == "warm_vivid":
        f[:,:,0] = np.clip(f[:,:,0] * 1.12, 0, 1)
        f[:,:,1] = np.clip(f[:,:,1] * 1.04, 0, 1)
        gray = (0.299*f[:,:,0] + 0.587*f[:,:,1] + 0.114*f[:,:,2])[:,:,np.newaxis]
        f = np.clip(gray + (f - gray) * 1.3, 0, 1)
    elif style == "dark_finance":
        f = np.clip((f - 0.5) * 1.25 + 0.48, 0, 1)
        f[:,:,2] = np.clip(f[:,:,2] * 1.06, 0, 1)
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


def _apply_grade(clip, style):
    if not style or style == "realistic":
        return clip
    try:
        return clip.image_transform(lambda frame: _grade_frame(frame, style))
    except AttributeError:
        try:
            return clip.fl_image(lambda frame: _grade_frame(frame, style))
        except Exception:
            return clip


# ── Audio helpers ─────────────────────────────────────────────────────────────

def _loop_audio(clip, duration):
    if clip.duration >= duration:
        return clip.subclipped(0, duration)
    times = math.ceil(duration / clip.duration)
    return concatenate_audioclips([clip] * times).subclipped(0, duration)


def _scale_volume(clip, factor):
    try:
        from moviepy.audio.fx import MultiplyVolume
        return clip.with_effects([MultiplyVolume(factor)])
    except Exception:
        pass
    for m in ("with_volume_scaled", "with_volume_scaling", "volumex"):
        if hasattr(clip, m):
            try:
                return getattr(clip, m)(factor)
            except Exception:
                continue
    return clip


def _build_sfx_track(cut_times, total_duration, sfx_path, fps=44100):
    """Build an SFX audio track with a whoosh at every clip cut point."""
    try:
        sfx_clip = AudioFileClip(sfx_path)
        sfx_arr = sfx_clip.to_soundarray(fps=fps)
        sfx_clip.close()
        if sfx_arr.ndim == 1:
            sfx_arr = np.column_stack([sfx_arr, sfx_arr])
        total_samples = int(total_duration * fps)
        track = np.zeros((total_samples, 2), dtype=np.float32)
        sfx_len = len(sfx_arr)
        for t in cut_times:
            start = int(t * fps)
            end = min(start + sfx_len, total_samples)
            track[start:end] += sfx_arr[:end-start] * 0.5   # 50% volume
        # Create AudioClip from array
        try:
            from moviepy import AudioArrayClip
            return AudioArrayClip(track, fps=fps)
        except Exception:
            arr = track
            def make_frame(t):
                idx = int(t * fps)
                return arr[idx] if idx < len(arr) else np.zeros(2)
            from moviepy import AudioClip
            return AudioClip(make_frame, duration=total_duration, fps=fps)
    except Exception as e:
        print(f"⚠️  SFX track build failed: {e} — skipping SFX.")
        return None


# ── Freesound downloads ───────────────────────────────────────────────────────

def _download_background_music(theme_keyword, output_path):
    print(f"🎵 Searching background music: '{theme_keyword}'...")
    if not FREESOUND_API_KEY:
        print("⚠️  No FREESOUND_API_KEY — skipping.")
        return
    url = (
        f"https://freesound.org/apiv2/search/text/"
        f"?query={theme_keyword} ambient loop"
        f"&fields=id,name,previews&token={FREESOUND_API_KEY}&page_size=1"
    )
    try:
        res = requests.get(url, timeout=20).json()
        results = res.get("results") or []
        if not results:
            return
        audio_url = results[0]["previews"]["preview-hq-mp3"]
        print(f"📥 Downloading: {results[0]['name']}")
        with open(output_path, "wb") as f:
            f.write(requests.get(audio_url, timeout=30).content)
    except Exception as e:
        print(f"⚠️  Music download failed: {e}")


def _download_sfx(output_path):
    """Download a subtle transition whoosh SFX from Freesound."""
    if not FREESOUND_API_KEY:
        return
    url = (
        f"https://freesound.org/apiv2/search/text/"
        f"?query=whoosh transition short&fields=id,name,previews,duration"
        f"&token={FREESOUND_API_KEY}&page_size=5"
    )
    try:
        res = requests.get(url, timeout=20).json()
        results = res.get("results") or []
        # Pick a short whoosh (under 2 seconds)
        for r in results:
            if r.get("duration", 99) <= 2.0:
                audio_url = r["previews"]["preview-hq-mp3"]
                with open(output_path, "wb") as f:
                    f.write(requests.get(audio_url, timeout=20).content)
                print(f"🔊 SFX downloaded: {r['name']}")
                return
        # Fallback: just use first result
        if results:
            audio_url = results[0]["previews"]["preview-hq-mp3"]
            with open(output_path, "wb") as f:
                f.write(requests.get(audio_url, timeout=20).content)
    except Exception as e:
        print(f"⚠️  SFX download failed: {e}")


# ── Pexels clip fetching ──────────────────────────────────────────────────────

def _fetch_pexels_clip_urls(keyword, count, headers, used_urls):
    collected = []
    per_page = min(max(count + 6, 12), 15)

    def _search(q, page=1):
        url = (
            "https://api.pexels.com/videos/search"
            f"?query={q}&per_page={per_page}&page={page}&orientation=landscape"
        )
        try:
            return requests.get(url, headers=headers, timeout=25).json().get("videos") or []
        except Exception as e:
            print(f"    ⚠️  Pexels search error: {e}")
            return []

    def _best_url(video):
        files = video.get("video_files", [])
        hd = [f for f in files if 1080 <= f.get("height", 0) <= 1440]
        if hd:
            return sorted(hd, key=lambda f: abs(f.get("height", 0)-1080))[0]["link"]
        return sorted(files, key=lambda f: f.get("width", 9999))[0]["link"] if files else None

    for page in range(1, 4):
        if len(collected) >= count:
            break
        for v in _search(keyword, page):
            vurl = _best_url(v)
            if vurl and vurl not in used_urls:
                collected.append(vurl)
                used_urls.add(vurl)
            if len(collected) >= count:
                break

    if len(collected) < count:
        for v in _search(keyword.split()[0]):
            vurl = _best_url(v)
            if vurl and vurl not in used_urls:
                collected.append(vurl)
                used_urls.add(vurl)
            if len(collected) >= count:
                break

    if len(collected) < count:
        for v in _search("business world"):
            vurl = _best_url(v)
            if vurl and vurl not in used_urls:
                collected.append(vurl)
                used_urls.add(vurl)
            if len(collected) >= count:
                break

    print(f"    ✅ {len(collected)}/{count} unique clips for '{keyword}'")
    return collected, used_urls


def _download_video(url, path, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            data = requests.get(url, timeout=60).content
            with open(path, "wb") as f:
                f.write(data)
            return
        except Exception as e:
            last_err = e
            wait = 2 ** attempt
            print(f"     ↩️  Retry {attempt+1} in {wait}s...")
            time.sleep(wait)
    raise last_err


# ── Main assembly ─────────────────────────────────────────────────────────────

def assemble_documentary(segments, video_theme, content_type="history", visual_style="realistic"):
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY not set in .env")

    headers = {"Authorization": PEXELS_API_KEY}
    used_urls  = set()
    final_clips = []
    temp_files  = []
    cut_times   = []      # cumulative timestamps of each clip cut (for SFX)
    cumulative  = 0.0

    print(f"\n🎬 Building {content_type} video — {len(segments)} segments | style: {visual_style}")

    try:
        # ── Download SFX and music early ─────────────────────────────────────
        sfx_path = "sfx_transition.mp3"
        bg_path  = "bg_music_temp.mp3"
        _download_sfx(sfx_path)
        if os.path.exists(sfx_path):
            temp_files.append(sfx_path)
        _download_background_music(video_theme, bg_path)
        if os.path.exists(bg_path):
            temp_files.append(bg_path)

        # ── Build each segment ────────────────────────────────────────────────
        for i, seg in enumerate(segments):
            print(f"\n  ▶  Segment {i+1}/{len(segments)} | '{seg['keyword']}'")

            audio_path = f"audio_{i}.mp3"
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Missing voiceover: {audio_path}")

            audio = AudioFileClip(audio_path)
            audio_dur = audio.duration

            clips_needed = max(2, math.ceil(audio_dur / CLIP_CUT_DURATION))
            print(f"     🎞️  {audio_dur:.1f}s → {clips_needed} clips")

            clip_urls, used_urls = _fetch_pexels_clip_urls(
                seg["keyword"], clips_needed, headers, used_urls
            )

            segment_clips = []
            accumulated = 0.0

            for j, vurl in enumerate(clip_urls):
                if accumulated >= audio_dur:
                    break
                clip_path = f"temp_{i}_{j}.mp4"
                temp_files.append(clip_path)
                try:
                    print(f"     ⬇️  Clip {j+1}/{len(clip_urls)}...")
                    _download_video(vurl, clip_path)
                    vc = VideoFileClip(clip_path).resized(OUTPUT_SIZE)
                    remaining = audio_dur - accumulated
                    cut_dur = min(CLIP_CUT_DURATION, remaining, vc.duration)
                    if cut_dur <= 0.1:
                        vc.close(); break
                    vc = vc.subclipped(0, cut_dur)
                    # Record cut times (start of each new clip = a cut point)
                    if segment_clips:   # don't record very first clip as a "cut"
                        cut_times.append(cumulative + accumulated)
                    segment_clips.append(vc)
                    accumulated += cut_dur
                except Exception as e:
                    print(f"     ⚠️  Clip {j+1} failed: {e}")
                    continue

            if not segment_clips:
                if final_clips:
                    print("     🔄  Falling back to previous segment visuals.")
                    prev = final_clips[-1].without_audio()
                    seg_video = _loop_audio_visual(prev, audio_dur).with_audio(audio)
                    final_clips.append(seg_video)
                    cumulative += audio_dur
                    continue
                else:
                    raise RuntimeError(f"No clips for segment {i+1}. Check internet + Pexels key.")

            seg_video = (
                segment_clips[0] if len(segment_clips) == 1
                else concatenate_videoclips(segment_clips, method="chain")
            )
            if seg_video.duration > audio_dur:
                seg_video = seg_video.subclipped(0, audio_dur)
            elif seg_video.duration < audio_dur - 0.1:
                audio = audio.subclipped(0, seg_video.duration)

            seg_video = seg_video.with_audio(audio)
            final_clips.append(seg_video)
            cumulative += seg_video.duration
            print(f"     ✅ Segment {i+1} — {seg_video.duration:.1f}s")

        # ── Concatenate all segments ──────────────────────────────────────────
        print("\n🖥️  Concatenating all segments...")
        full_doc = concatenate_videoclips(final_clips, method="chain")
        total_dur = full_doc.duration
        print(f"    Duration: {total_dur/60:.1f} min")

        # ── Apply color grade ─────────────────────────────────────────────────
        if visual_style and visual_style != "realistic":
            print(f"🎨 Applying color grade: {visual_style}...")
            full_doc = _apply_grade(full_doc, visual_style)

        # ── Build audio mix: voice 100% + music 30% + SFX 50% ────────────────
        audio_layers = [full_doc.audio]

        if os.path.exists(bg_path):
            print("🎵 Mixing background music at 30%...")
            bg = AudioFileClip(bg_path)
            bg = _loop_audio(bg, total_dur)
            bg = _scale_volume(bg, 0.30)
            audio_layers.append(bg)

        if os.path.exists(sfx_path) and cut_times:
            print(f"🔊 Building SFX track ({len(cut_times)} cut points)...")
            sfx_track = _build_sfx_track(cut_times, total_dur, sfx_path)
            if sfx_track:
                audio_layers.append(sfx_track)

        if len(audio_layers) > 1:
            full_doc = full_doc.with_audio(CompositeAudioClip(audio_layers))

        # ── Render ────────────────────────────────────────────────────────────
        output_path = "AmbientNest_Final_Output.mp4"
        print(f"\n🚀 Rendering {total_dur/60:.1f}-min video...")
        full_doc.write_videofile(
            output_path, fps=TARGET_FPS, codec="libx264",
            audio_codec="aac", threads=4, preset="fast",
        )
        return output_path

    finally:
        print("\n🧹 Cleaning temp files...")
        for path in temp_files:
            if os.path.exists(path):
                try: os.remove(path)
                except OSError: pass
        for i in range(len(segments)):
            p = f"audio_{i}.mp3"
            if os.path.exists(p):
                try: os.remove(p)
                except OSError: pass


def _loop_audio_visual(clip, duration):
    """Loop a video clip (visual only) to match a target duration."""
    if clip.duration >= duration:
        return clip.subclipped(0, duration)
    times = math.ceil(duration / clip.duration)
    return concatenate_videoclips([clip]*times, method="chain").subclipped(0, duration)