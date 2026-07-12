"""
AmbientNest HQ — Scary Stories Shorts Pipeline
Dark Fantasy art + Glitch effects + Red captions + Horror music
Smart scheduling based on YouTube Analytics audience data
3 Shorts per day, published at optimal engagement times
"""

import os, re, sys, json, math, time, asyncio, pickle, random
import subprocess, urllib.parse, datetime, requests
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types
import edge_tts
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY")
FREESOUND_API_KEY = os.environ.get("FREESOUND_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# ── Constants ─────────────────────────────────────────────────────────────────
W, H   = 1080, 1920
FPS    = 30
VOICE  = "en-US-GuyNeural"     # calm, deep, slightly eerie
RATE   = "-10%"                 # slower = creepier
PITCH  = "-5Hz"

# Dark fantasy Pollinations style
IMAGE_STYLE = (
    "dark fantasy digital art, gothic atmosphere, deep shadows, "
    "volumetric fog, cinematic horror lighting, hyper-detailed, "
    "eerie supernatural mood, ominous dark tones, dramatic composition"
)

# Horror music presets → Freesound search terms
MUSIC_PRESETS = [
    "creepy melody horror",
    "haunting piano dark",
    "horror piano suspense",
    "unsolved mystery suspense",
    "eerie ambient tension",
    "orchestral horror dramatic",
]

# Default posting hours (UTC) if no analytics data yet
DEFAULT_HOURS = [14, 18, 22]  # 2pm, 6pm, 10pm UTC


# ══════════════════════════════════════════════════════════════════════════════
# 1. SMART SCHEDULER — finds best hours from YouTube Analytics
# ══════════════════════════════════════════════════════════════════════════════

def get_best_posting_hours():
    """
    Query YouTube Analytics for hourly engagement data.
    Returns 3 optimal UTC hours to post Shorts today.
    Falls back to horror prime-time defaults if channel is new.
    """
    try:
        if not os.path.exists("token.pickle"):
            print("⏰ No auth found — using default schedule")
            return DEFAULT_HOURS

        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)

        analytics = build("youtubeAnalytics", "v2", credentials=creds)
        end_date   = datetime.date.today().isoformat()
        start_date = (datetime.date.today() - datetime.timedelta(days=28)).isoformat()

        response = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions="hour",
            sort="hour",
        ).execute()

        rows = response.get("rows", [])
        if not rows or len(rows) < 6:
            print("⏰ Not enough analytics data yet — using horror prime-time defaults")
            return DEFAULT_HOURS

        # Sort hours by combined views + watch time score
        scored = []
        for row in rows:
            hour, views, minutes = int(row[0]), float(row[1]), float(row[2])
            score = views * 0.4 + minutes * 0.6
            scored.append((score, hour))

        scored.sort(reverse=True)
        top_hours = sorted([h for _, h in scored[:3]])
        print(f"📊 Analytics best hours (UTC): {top_hours}")
        return top_hours

    except Exception as e:
        print(f"⚠️ Analytics query failed: {e} — using defaults")
        return DEFAULT_HOURS


def build_publish_times(hours_utc):
    """Convert UTC hours to ISO 8601 publish timestamps for today."""
    today = datetime.date.today()
    times = []
    for h in hours_utc:
        dt = datetime.datetime(today.year, today.month, today.day, h, 0, 0,
                               tzinfo=datetime.timezone.utc)
        # If time already passed today, push to tomorrow
        if dt < datetime.datetime.now(datetime.timezone.utc):
            dt += datetime.timedelta(days=1)
        times.append(dt.isoformat())
    return times


# ══════════════════════════════════════════════════════════════════════════════
# 2. STORY GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def find_scary_story(used=""):
    """Gemini searches for the scariest real story/urban legend right now."""
    print("👻 Searching for scary story...")
    exclude = f"Do NOT use: {used}" if used else ""

    search_prompt = f"""
    Search the web and find ONE deeply terrifying, true scary story.
    It can be:
    - A real paranormal or unexplained event with witnesses
    - An urban legend with documented real-world origins
    - A true crime case with horror elements
    - A historical event so disturbing it sounds fictional
    - A scientific phenomenon that defies explanation
    
    It MUST:
    - Be genuinely spine-chilling and hard to believe
    - Have enough detail for a 60-second narration
    - Have a twist, dark revelation, or deeply unsettling ending
    - Be relatively unknown — not Slenderman or Bloody Mary
    {exclude}
    
    Describe the story in 150-200 words with all key details.
    """

    search_resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=search_prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    raw_story = search_resp.text.strip()

    # Structure into script
    script_prompt = f"""
    Turn this scary story into a YouTube Shorts script. 60 seconds max.
    
    Story: {raw_story}
    
    Return ONLY raw JSON (no markdown):
    {{
      "title": "Ultra clickable Short title under 80 chars. Use 'This is REAL', 'True Story', 'Nobody Talks About This'. Include #Shorts",
      "description": "3 lines. Hook. What happened. Subscribe line. End with: #ScaryStories #AmbientNestHQ #Horror #Paranormal #TrueStory #Scary #Creepy #shorts",
      "tags": ["20 tags: scary stories, horror, paranormal, true story, creepy, ambientnesthq, viral, unexplained, dark, disturbing, chilling, haunted, ghost, supernatural, mystery, scary shorts, horror shorts, true horror, real ghost, disturbing facts"],
      "hook": "The single most disturbing sentence from the story — 10 words max",
      "full_narration": "The complete 60-second spoken script. Calm, slow, first person where possible. Build dread. End with a gut-punch final line.",
      "scenes": [
        {{
          "text": "3-4 sentences of narration for this scene",
          "image_prompt": "Specific dark fantasy visual description for this moment in the story"
        }}
      ]
    }}
    
    Make exactly 5 scenes. Total narration = 60 seconds when read slowly.
    """

    json_resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=script_prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    script = json.loads(json_resp.text.strip())
    print(f"✅ Story: {script.get('title','')[:60]}")
    return script


# ══════════════════════════════════════════════════════════════════════════════
# 3. VOICEOVER
# ══════════════════════════════════════════════════════════════════════════════

async def make_voiceover(text, path):
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    await comm.save(path)


def get_audio_duration(path):
    try:
        r = subprocess.run(
            ["ffprobe","-v","error","-show_entries","format=duration",
             "-of","default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True
        )
        return float(r.stdout.strip())
    except Exception:
        try:
            from mutagen.mp3 import MP3
            return MP3(path).info.length
        except Exception:
            return 11.0


# ══════════════════════════════════════════════════════════════════════════════
# 4. IMAGE GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def generate_image(prompt, path):
    full = f"{prompt}, {IMAGE_STYLE}"
    encoded = urllib.parse.quote(full)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={W}&height={H}&nologo=true&enhance=true"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(path, "wb") as f:
                    f.write(r.content)
                return True
        except Exception as e:
            print(f"    ⚠️ Image attempt {attempt+1}: {e}")
        time.sleep(4)
    # Fallback: dark purple frame
    subprocess.run([
        "ffmpeg","-y","-f","lavfi",
        f"-i","color=c=0x1a0a2e:size={W}x{H}:rate=1",
        "-frames:v","1", path
    ], capture_output=True)
    return False


# ══════════════════════════════════════════════════════════════════════════════
# 5. HORROR MUSIC
# ══════════════════════════════════════════════════════════════════════════════

def download_horror_music(path):
    if not FREESOUND_API_KEY:
        print("⚠️ No FREESOUND_API_KEY — skipping music")
        return False

    query = random.choice(MUSIC_PRESETS)
    print(f"🎵 Fetching horror music: '{query}'...")

    url = (
        f"https://freesound.org/apiv2/search/text/"
        f"?query={urllib.parse.quote(query)}"
        f"&fields=id,name,previews,duration"
        f"&token={FREESOUND_API_KEY}&page_size=5"
    )
    try:
        res = requests.get(url, timeout=20).json()
        results = [r for r in (res.get("results") or []) if r.get("duration",0) > 20]
        if not results:
            return False
        track = random.choice(results)
        audio_url = track["previews"]["preview-hq-mp3"]
        with open(path, "wb") as f:
            f.write(requests.get(audio_url, timeout=30).content)
        print(f"✅ Music: {track['name']}")
        return True
    except Exception as e:
        print(f"⚠️ Music failed: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# 6. RED CAPTIONS — ASS subtitle file
# ══════════════════════════════════════════════════════════════════════════════

def generate_captions(full_narration, total_duration, path):
    """Generate ASS subtitle file with red bold word-group captions."""
    words = full_narration.split()
    chunk_size = 4
    chunks = [words[i:i+chunk_size] for i in range(0, len(words), chunk_size)]
    time_per_chunk = total_duration / max(len(chunks), 1)

    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    header = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Scary,Arial,58,&H000000FF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,1.2,0,1,3,1,2,40,40,220,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    # Red = &H000000FF in ASS (AABBGGRR)
    lines = []
    for i, chunk in enumerate(chunks):
        start = i * time_per_chunk
        end = min((i + 1) * time_per_chunk, total_duration)
        text = " ".join(chunk).upper()
        lines.append(f"Dialogue: 0,{fmt(start)},{fmt(end)},Scary,,0,0,0,,{text}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines))


# ══════════════════════════════════════════════════════════════════════════════
# 7. VIDEO ASSEMBLY — animate + glitch + captions + music
# ══════════════════════════════════════════════════════════════════════════════

def animate_scene(img_path, audio_path, out_path, idx):
    """Animate image with pan/zoom + chromatic glitch effect."""
    dur = get_audio_duration(audio_path)
    OW, OH = int(W*1.2), int(H*1.2)
    dx, dy = OW-W, OH-H

    # Different pan direction per scene
    pans = [
        f"scale={OW}:{OH},crop={W}:{H}:'t/{dur}*{dx}':{dy//2}",
        f"scale={OW}:{OH},crop={W}:{H}:{dx//2}:'t/{dur}*{dy}'",
        f"scale={OW}:{OH},crop={W}:{H}:'{dx}-t/{dur}*{dx}':{dy//2}",
        f"scale={OW}:{OH},crop={W}:{H}:{dx//2}:'{dy}-t/{dur}*{dy}'",
        f"scale={OW}:{OH},crop={W}:{H}:'(iw-{W})/2*t/{dur}':{dy//2}",
    ]
    pan = pans[idx % len(pans)]

    # Chromatic aberration glitch — shifts R and B channels horizontally
    # Triggers on bands every ~50px, shifts every 5 frames = real horror glitch
    glitch = (
        "geq="
        "r='if(lt(mod(floor(Y/60)+floor(N/4),4),1),r(X+5,Y),r(X,Y))':"
        "g='g(X,Y)':"
        "b='if(lt(mod(floor(Y/60)+floor(N/4),4),1),b(X-5,Y),b(X,Y))'"
    )

    # Subtle vignette for horror feel
    vignette = "vignette=PI/3"

    vf = f"{pan},{glitch},{vignette}"

    cmd = [
        "ffmpeg","-y",
        "-loop","1","-framerate",str(FPS),"-i", img_path,
        "-i", audio_path,
        "-vf", vf,
        "-c:v","libx264","-preset","ultrafast","-tune","stillimage","-crf","23",
        "-c:a","aac","-b:a","128k",
        "-t", str(dur), "-pix_fmt","yuv420p","-shortest",
        out_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Scene {idx} failed: {result.stderr.decode()[-200:]}")
    print(f"  🎬 Scene {idx+1} ({dur:.1f}s) — glitch applied")


def assemble_short(scene_clips, captions_path, music_path, out_path, series_name):
    """Concatenate scenes, burn red captions, mix horror music."""
    print("✂️  Stitching scenes...")

    # Concat
    with open("sc_concat.txt","w") as f:
        for c in scene_clips:
            f.write(f"file '{c}'\n")

    temp1 = "sc_temp1.mp4"
    subprocess.run([
        "ffmpeg","-y","-f","concat","-safe","0",
        "-i","sc_concat.txt","-c","copy", temp1
    ], capture_output=True, check=True)

    # Burn captions + channel tag
    temp2 = "sc_temp2.mp4"
    vf_parts = []

    # Red captions via ASS subtitles
    if os.path.exists(captions_path):
        # Use subtitles filter with ASS file
        safe_path = captions_path.replace("\\", "/").replace(":", "\\:")
        vf_parts.append(f"subtitles={safe_path}")

    # Channel watermark bottom
    vf_parts.append(
        "drawtext=text='AMBIENTNEST HQ':"
        "fontsize=28:fontcolor=white@0.5:"
        "x=(w-text_w)/2:y=h-60:"
        "shadowcolor=black@0.8:shadowx=1:shadowy=1"
    )

    subprocess.run([
        "ffmpeg","-y","-i", temp1,
        "-vf", ",".join(vf_parts),
        "-c:v","libx264","-preset","fast",
        "-c:a","aac","-b:a","128k","-pix_fmt","yuv420p",
        temp2
    ], capture_output=True, check=True)

    # Mix horror music at 20% volume
    if music_path and os.path.exists(music_path):
        print("🎵 Mixing horror music...")
        subprocess.run([
            "ffmpeg","-y",
            "-i", temp2,
            "-stream_loop","-1","-i", music_path,
            "-filter_complex",
            "[0:a]volume=1.0[voice];[1:a]volume=0.20[music];[voice][music]amix=inputs=2:duration=first[aout]",
            "-map","0:v","-map","[aout]",
            "-c:v","copy","-c:a","aac","-b:a","128k",
            "-shortest", out_path
        ], capture_output=True, check=True)
    else:
        os.rename(temp2, out_path)

    # Cleanup temp files
    for f in ["sc_concat.txt", temp1]:
        if os.path.exists(f): os.remove(f)
    if os.path.exists(temp2) and os.path.exists(out_path):
        try: os.remove(temp2)
        except: pass

    print(f"✅ Short assembled: {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# 8. YOUTUBE UPLOAD WITH SMART SCHEDULING
# ══════════════════════════════════════════════════════════════════════════════

def upload_scheduled(video_path, title, description, tags, publish_at):
    """Upload as private with scheduled publish time."""
    if not os.path.exists("token.pickle"):
        print("❌ token.pickle missing")
        return None

    with open("token.pickle","rb") as f:
        creds = pickle.load(f)

    youtube = build("youtube","v3", credentials=creds)

    def clean_tags(tags):
        clean, total = [], 0
        for t in tags:
            t = re.sub(r"[^a-zA-Z0-9 \-]","",str(t)).strip()
            if not t or len(t)>30 or total+len(t)>490: continue
            clean.append(t); total+=len(t)+1
        return clean or ["ScaryStories","AmbientNestHQ"]

    if "#Shorts" not in title and "#shorts" not in title:
        title = title[:85]+" #Shorts"

    body = {
        "snippet":{
            "title": title[:100],
            "description": description,
            "tags": clean_tags(tags),
            "categoryId": "24",  # Entertainment
        },
        "status":{
            "privacyStatus": "private",
            "publishAt": publish_at,  # Auto-goes public at this time
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    try:
        resp = youtube.videos().insert(
            part="snippet,status", body=body, media_body=media
        ).execute()
        vid = resp["id"]
        print(f"✅ Scheduled for {publish_at}: https://youtube.com/shorts/{vid}")
        return vid
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 9. MASTER PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

async def create_one_scary_short(short_num, publish_at, used_topics=""):
    print(f"\n{'='*55}")
    print(f"👻 Creating Scary Short #{short_num} | Publishes: {publish_at}")
    print(f"{'='*55}")

    temp_files = []

    try:
        # Generate story + script
        script = find_scary_story(used_topics)
        scenes = script.get("scenes", [])
        full_narration = script.get("full_narration","")

        if not scenes:
            raise RuntimeError("No scenes generated")

        # Generate voiceovers + images per scene
        scene_clips = []
        for i, scene in enumerate(scenes):
            audio_path = f"sc_audio_{i}.mp3"
            img_path   = f"sc_img_{i}.jpg"
            clip_path  = f"sc_clip_{i}.mp4"
            temp_files += [audio_path, img_path, clip_path]

            # Voiceover
            await make_voiceover(scene["text"], audio_path)
            print(f"  🎙️ Scene {i+1} voice done")

            # Dark fantasy image
            full_prompt = f"{scene['image_prompt']}, {IMAGE_STYLE}"
            generate_image(full_prompt, img_path)
            print(f"  🎨 Scene {i+1} image done")

            # Animate with glitch
            animate_scene(img_path, audio_path, clip_path, i)
            scene_clips.append(clip_path)

        # Get total duration for captions
        total_dur = sum(get_audio_duration(f"sc_audio_{i}.mp3") for i in range(len(scenes)))

        # Red captions
        captions_path = f"sc_captions_{short_num}.ass"
        temp_files.append(captions_path)
        generate_captions(full_narration, total_dur, captions_path)
        print(f"📝 Red captions generated")

        # Horror music
        music_path = f"sc_music_{short_num}.mp3"
        temp_files.append(music_path)
        has_music = download_horror_music(music_path)
        if not has_music:
            music_path = None

        # Assemble final Short
        output = f"AmbientNest_Scary_{short_num:02d}.mp4"
        assemble_short(scene_clips, captions_path, music_path, output, "AmbientNest HQ")

        # Upload with smart schedule
        vid_id = upload_scheduled(
            output,
            script.get("title", "This TRUE Story Will Haunt You #Shorts"),
            script.get("description",""),
            script.get("tags", ["ScaryStories","AmbientNestHQ","shorts"]),
            publish_at,
        )

        return script.get("title",""), vid_id

    finally:
        print("🧹 Cleaning up...")
        for f in temp_files:
            if f and os.path.exists(f):
                try: os.remove(f)
                except: pass
        output_name = f"AmbientNest_Scary_{short_num:02d}.mp4"
        if os.path.exists(output_name):
            try: os.remove(output_name)
            except: pass


async def run():
    print("="*55)
    print("👻 AmbientNest HQ — Scary Stories Shorts")
    print("="*55)

    # Get best posting times from analytics
    best_hours = get_best_posting_hours()
    publish_times = build_publish_times(best_hours)
    print(f"📅 Scheduled publish times: {publish_times}")

    used = ""
    for i, publish_at in enumerate(publish_times, 1):
        title, vid = await create_one_scary_short(i, publish_at, used)
        used += f", {title}"
        print(f"\n✅ Short {i}/3 scheduled!")

    print(f"\n🏁 All 3 Scary Shorts scheduled for today!")


if __name__ == "__main__":
    asyncio.run(run())