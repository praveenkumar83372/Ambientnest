import os
import re
import json
import pickle
import asyncio
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from content_engine import detect_slot, get_slot_content, SLOTS
from voice_engine import generate_voiceover
from video_engine import assemble_documentary
from thumbnail import generate_thumbnail, upload_thumbnail

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env")

client = genai.Client(api_key=GEMINI_API_KEY)


# 1. SCRIPT GENERATION ─────────────────────────────────────────────────────────
def generate_script(slot_content):
    import datetime
    today = datetime.date.today().strftime("%B %d, %Y")
    label      = slot_content["label"]
    raw_news   = slot_content["raw_news"]
    thin       = slot_content["news_is_thin"]
    fallback   = slot_content["fallback_topic"]
    categories = ", ".join(slot_content["categories"])

    if thin:
        decision = f'content_type = "story". Build a compelling, detailed video about: "{fallback}"'
        target   = "4-5 minutes total narration → 6-8 segments"
    else:
        decision = 'content_type = "news". Build an engaging real-time briefing from the news above.'
        target   = "6-8 minutes total narration → 9-12 segments"

    prompt = f"""
    You are the creative director of AmbientNest HQ — a YouTube channel covering
    Finance, AI, History, Science, Travel, Psychology and fascinating world stories.
    Today: {today}. This video's category: {label}.

    Real-time findings:
    ---
    {raw_news or "No real-time data available."}
    ---

    DECISION (do not override): {decision}
    TARGET: {target}
    Each segment text = 5-8 natural spoken sentences (~35-50 seconds when read aloud).
    Write like a top BBC/Netflix documentary narrator — vivid, specific, no filler.

    Output ONE raw JSON object (no markdown, no code fences):
    {{
      "content_type": "news" or "story",
      "topic": "concise internal label",
      "theme": "background music mood keyword e.g. 'tense cinematic', 'ambient wonder', 'dramatic orchestral'",
      "title": "Magnetic YouTube title under 90 chars. Use power words, numbers, mystery, or urgency. Make someone STOP scrolling. No lies.",
      "description": "4-6 sentences. Open with a curiosity hook. Weave in keywords naturally. Tell viewers exactly what they will learn. End with: Like, Subscribe and hit the bell for daily stories from around the world. Then NEW LINE: 10-15 hashtags always including #AmbientNestHQ #WorldStories #MindBlowing plus topic-specific trending ones.",
      "tags": ["25-30 tags no # symbol — mix: specific topic, broad interest tags like 'mind blowing facts' 'untold stories' 'world history', channel tags 'AmbientNestHQ' 'AmbientNest', trending YouTube search terms, content style tags 'documentary' 'explained' 'facts' 'story time'"],
      "segments": [
        {{
          "text": "Compelling spoken narration — vivid, specific, real names/numbers. 5-8 sentences. No bullets.",
          "keyword": "specific Pexels video search term matching this segment visually"
        }}
      ]
    }}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    try:
        payload = json.loads(response.text.strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini JSON error: {e}\nRaw: {response.text[:400]}")

    print(f"📝 {len(payload.get('segments',[]))} segments | Title: {payload.get('title')}")
    return payload


# 2. YOUTUBE UPLOAD ────────────────────────────────────────────────────────────
def upload_to_youtube(video_path, title, description, tags):
    print("🚀 Uploading to YouTube...")
    if not os.path.exists("token.pickle"):
        print("❌ token.pickle missing. Run youtube_auth.py first.")
        return None
    with open("token.pickle", "rb") as f:
        creds = pickle.load(f)
    youtube = build("youtube", "v3", credentials=creds)

    def _clean_tags(tags):
        clean, total = [], 0
        for t in tags:
            t = re.sub(r"[^a-zA-Z0-9 \-]", "", str(t)).strip()
            if not t or len(t) > 30 or total + len(t) > 490:
                continue
            clean.append(t)
            total += len(t) + 1
        return clean or ["AmbientNestHQ", "world stories"]

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": _clean_tags(tags),
            "categoryId": "27",
        },
        "status": {"privacyStatus": "public"},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    try:
        print(f"🎬 Uploading: '{title}'...")
        resp = request.execute()
        vid = resp["id"]
        print(f"✅ Live: https://youtu.be/{vid}")
        return vid
    except Exception as e:
        print(f"❌ Upload failed: {e}\n   Video saved locally: {video_path}")
        return None


# 3. SINGLE VIDEO PIPELINE ────────────────────────────────────────────────────
async def produce_one_video(slot_content, output_filename="AmbientNest_Output.mp4"):
    script = generate_script(slot_content)
    segments   = script.get("segments") or []
    voice_key  = slot_content["voice"]
    style      = slot_content["style"]
    theme      = script.get("theme", slot_content["music"])
    c_type     = script.get("content_type", "story")

    if not segments:
        print("❌ No segments. Skipping.")
        return

    # Voiceovers
    print(f"\n🎙️  {len(segments)} voiceovers — voice: {voice_key}")
    for i, seg in enumerate(segments):
        print(f"  🔊 {i+1}/{len(segments)}")
        await generate_voiceover(seg["text"], f"audio_{i}.mp3", voice_key)

    # Render
    output_path = assemble_documentary(segments, theme, c_type, style)
    if output_filename != "AmbientNest_Final_Output.mp4" and os.path.exists("AmbientNest_Final_Output.mp4"):
        os.rename("AmbientNest_Final_Output.mp4", output_filename)
        output_path = output_filename

    print(f"\n🏁 Render complete: {output_path}")

    # Upload
    title  = script.get("title") or f"{script.get('topic')} | AmbientNest HQ"
    desc   = script.get("description") or "World stories from AmbientNest HQ."
    tags   = script.get("tags") or ["AmbientNestHQ", "world stories"]
    vid_id = upload_to_youtube(output_path, title, desc, tags)

    # Thumbnail
    if vid_id and os.path.exists(output_path):
        thumb = generate_thumbnail(output_path, title)
        upload_thumbnail(vid_id, thumb)


# 4. MASTER PIPELINE ──────────────────────────────────────────────────────────
async def run_pipeline():
    slot_num     = detect_slot()
    slot_content = get_slot_content(client, slot_num)

    print(f"\n🎬 Slot {slot_num}: {slot_content['label']}")
    print(f"   Voice: {slot_content['voice']} | Style: {slot_content['style']}")
    print(f"   News thin: {slot_content['news_is_thin']}")

    fname = f"AmbientNest_Slot{slot_num}.mp4"
    await produce_one_video(slot_content, fname)
    print(f"\n✅ Slot {slot_num} complete!")


if __name__ == "__main__":
    asyncio.run(run_pipeline())