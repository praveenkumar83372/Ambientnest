"""
Produces the 60-second Short teaser for each episode.
Uses Pollinations.ai for images + series-specific visual treatment.
"""

import os
import re
import subprocess
import pickle
import urllib.parse
import time
import requests
import asyncio
import edge_tts
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

WIDTH  = 1080
HEIGHT = 1920
FPS    = 30


# ── Image generation ──────────────────────────────────────────────────────────

def generate_image(prompt, output_path, width=WIDTH, height=HEIGHT):
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&enhance=true"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(output_path, "wb") as f:
                    f.write(r.content)
                return True
            time.sleep(4)
        except Exception as e:
            print(f"    ⚠️ Image attempt {attempt+1}: {e}")
            time.sleep(4)
    return False


# ── Color grade ───────────────────────────────────────────────────────────────

def get_color_filter(color_grade):
    filters = {
        "sepia":       "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,eq=contrast=1.1:brightness=-0.02",
        "cyberpunk":   "eq=saturation=1.3:contrast=1.3,colorchannelmixer=0.6:0:0.2:0:0:0.8:0:0:0.2:0:1.4",
        "horror":      "eq=contrast=1.4:brightness=-0.1:saturation=0.6,colorchannelmixer=1.3:0:0:0:0:0.7:0:0:0:0:0.7",
        "dark_finance":"eq=contrast=1.3:brightness=-0.08:saturation=0.8",
        "warm_vivid":  "eq=saturation=1.5:contrast=1.1:brightness=0.03,colorchannelmixer=1.1:0:0:0:0:1:0:0:0:0:0.9",
    }
    return filters.get(color_grade, "")


# ── Voiceover ─────────────────────────────────────────────────────────────────

async def generate_voiceover(text, path, voice, rate):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(path)


# ── Animate scene ─────────────────────────────────────────────────────────────

def animate_scene(image_path, audio_path, output_path, scene_index, color_grade):
    # Get audio duration
    duration = 11.0
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ], capture_output=True, text=True)
        duration = float(result.stdout.strip())
    except Exception:
        try:
            from mutagen.mp3 import MP3
            duration = MP3(audio_path).info.length
        except Exception:
            pass

    OW, OH = int(WIDTH * 1.2), int(HEIGHT * 1.2)
    dx, dy = OW - WIDTH, OH - HEIGHT

    animations = [
        f"scale={OW}:{OH},crop={WIDTH}:{HEIGHT}:'(iw-{WIDTH})/2*t/{duration}':{dy//2}",
        f"scale={OW}:{OH},crop={WIDTH}:{HEIGHT}:'t/{duration}*{dx}':{dy//2}",
        f"scale={OW}:{OH},crop={WIDTH}:{HEIGHT}:{dx//2}:'t/{duration}*{dy}'",
        f"scale={OW}:{OH},crop={WIDTH}:{HEIGHT}:'{dx}-t/{duration}*{dx}':{dy//2}",
        f"scale={OW}:{OH},crop={WIDTH}:{HEIGHT}:{dx//2}:'{dy}-t/{duration}*{dy}'",
    ]

    vf_parts = [animations[scene_index % len(animations)]]
    color_f = get_color_filter(color_grade)
    if color_f:
        vf_parts.append(color_f)
    vf_parts.append("vignette=PI/4")
    vf_parts.append(
        "drawtext=text='AMBIENTNEST HQ':"
        "fontsize=32:fontcolor=white@0.7:"
        "x=(w-text_w)/2:y=h-70:"
        "shadowcolor=black@0.8:shadowx=2:shadowy=2"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", image_path,
        "-i", audio_path,
        "-vf", ",".join(vf_parts),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-tune", "stillimage", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        "-pix_fmt", "yuv420p", "-shortest",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr.decode()[-200:]}")
    print(f"  🎬 Scene {scene_index+1} animated ({duration:.1f}s)")


# ── Stitch ────────────────────────────────────────────────────────────────────

def stitch_scenes(clips, output_path, series_name):
    with open("short_concat.txt", "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")

    temp = "short_temp_concat.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "short_concat.txt", "-c", "copy", temp
    ], capture_output=True, check=True)

    # Add series watermark
    vf = (
        f"drawtext=text='{series_name.upper()}':"
        f"fontsize=28:fontcolor=white@0.5:"
        f"x=20:y=40:shadowcolor=black@0.8:shadowx=1:shadowy=1"
    )

    subprocess.run([
        "ffmpeg", "-y", "-i", temp,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p", output_path
    ], capture_output=True, check=True)

    os.remove(temp)
    if os.path.exists("short_concat.txt"):
        os.remove("short_concat.txt")


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_short(video_path, title, description, tags):
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
            clean.append(t)
            total += len(t) + 1
        return clean or ["Shorts", "AmbientNestHQ"]

    if "#Shorts" not in title and "#shorts" not in title:
        title = title[:85] + " #Shorts"

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
        print(f"✅ Short live: https://youtube.com/shorts/{vid}")
        return vid
    except Exception as e:
        print(f"❌ Short upload failed: {e}")
        return None


# ── Master Short pipeline ─────────────────────────────────────────────────────

async def produce_short(series, short_script, episode_number):
    print(f"\n📱 Producing Short for {series['name']} EP{episode_number}...")
    scenes = short_script.get("scenes", [])
    voice = series["voice"]
    rate = series["voice_rate"]
    color_grade = series["color_grade"]
    image_style = series["image_style"]
    temp_files = []

    try:
        # Generate voiceovers + images
        for i, scene in enumerate(scenes):
            audio_path = f"s_audio_{i}.mp3"
            img_path = f"s_img_{i}.jpg"
            temp_files += [audio_path, img_path]

            await generate_voiceover(scene["narration"], audio_path, voice, rate)
            full_prompt = f"{scene['image_prompt']}, {image_style}"
            success = generate_image(full_prompt, img_path)
            if not success:
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"color=c=1a1a2e:size={WIDTH}x{HEIGHT}:rate=1",
                    "-frames:v", "1", img_path
                ], capture_output=True)

        # Animate each scene
        scene_clips = []
        for i in range(len(scenes)):
            clip = f"s_scene_{i}.mp4"
            temp_files.append(clip)
            animate_scene(f"s_img_{i}.jpg", f"s_audio_{i}.mp3", clip, i, color_grade)
            scene_clips.append(clip)

        # Stitch
        output = f"AmbientNest_Short_EP{episode_number:03d}.mp4"
        stitch_scenes(scene_clips, output, series["name"])
        print(f"✅ Short rendered: {output}")

        # Upload
        vid_id = upload_short(
            output,
            short_script.get("short_title", f"{series['name']} #{episode_number} #Shorts"),
            short_script.get("short_description", ""),
            short_script.get("short_tags", ["Shorts", "AmbientNestHQ"]),
        )

        return output, vid_id

    finally:
        for f in temp_files:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass