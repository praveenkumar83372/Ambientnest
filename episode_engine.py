"""
Episode script generator.
Produces two scripts per episode:
  1. Full video script (8-10 min, 12-15 segments)
  2. Short teaser script (60 sec, 5 scenes — the most gripping moment)
Both scripts are tailored to the series' unique tone and style.
"""

import json
from google.genai import types


def generate_episode_scripts(client, series, episode_number, used_topics=""):
    """
    Generate both full video and Short scripts for one episode.
    Returns dict with 'full' and 'short' scripts.
    """
    print(f"🔍 Finding story for {series['name']} Episode {episode_number}...")

    # Step 1: Find the story
    story = _discover_story(client, series, used_topics)

    # Step 2: Generate full video script
    print(f"📝 Writing full episode script...")
    full_script = _generate_full_script(client, series, story, episode_number)

    # Step 3: Generate Short teaser from the most gripping moment
    print(f"📱 Writing Short teaser script...")
    short_script = _generate_short_script(client, series, story, full_script)

    return {
        "story": story,
        "full": full_script,
        "short": short_script,
    }


def _discover_story(client, series, used_topics=""):
    """Find a real, compelling story for this series."""
    categories = ", ".join(series["categories"])
    exclude = f"\nDo NOT use: {used_topics}" if used_topics else ""
    series_name = series["name"]
    tagline = series["tagline"]

    prompt = f"""
    Search the web and find ONE real, compelling, deeply fascinating story for
    the YouTube series "{series_name}" — {tagline}

    Story must fit these categories: {categories}
    {exclude}

    Requirements:
    - Must be a REAL documented event or person
    - Must have genuine emotional weight — shocking, haunting, inspiring, or chilling
    - Must have enough detail to fill 8-10 minutes of storytelling
    - Must be relatively unknown to general audiences (not overdone)
    - Must have a strong narrative arc (beginning, tension, revelation, aftermath)

    Respond with ONLY a JSON object:
    {{
      "title": "The story title",
      "subject": "Main person/event name",
      "year": "Year or era",
      "location": "Where it happened",
      "one_line": "One shocking sentence that captures the essence",
      "key_facts": ["5-7 specific real facts about this story"]
    }}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            response_mime_type="application/json",
        ),
    )

    try:
        story = json.loads(response.text.strip())
        print(f"✅ Story found: {story.get('title')} ({story.get('year')})")
        return story
    except Exception as e:
        raise RuntimeError(f"Story discovery failed: {e}")


def _generate_full_script(client, series, story, episode_number):
    """Generate the full 8-10 minute episode script."""
    series_name = series["name"]
    hook = series["hook_template"]
    image_style = series["image_style"]
    prefix = series["episode_prefix"]

    prompt = f"""
    You are writing Episode {episode_number} of "{series_name}" for AmbientNest HQ.

    Story: {json.dumps(story)}
    Series hook template: "{hook}"

    Write a deeply immersive, emotionally gripping 8-10 minute script.
    Tone: {series['tagline']}
    Voice style: First person where appropriate, present tense for tension moments.
    Structure: Cold open hook → Build → Revelation → Aftermath → Haunting ending

    Rules:
    - 12-14 segments
    - Each segment = 5-8 natural spoken sentences (35-50 seconds)
    - Use specific real details, names, dates, places from the story
    - Create visceral sensory details (what they heard, smelled, felt)
    - End each segment on a micro-cliffhanger or revelation
    - The FINAL segment must leave the audience wanting more

    Output ONE raw JSON object (no markdown):
    {{
      "episode_title": "Full episode title — gripping, specific, under 90 chars",
      "series_episode": "{series_name} | {prefix}{episode_number:03d}",
      "description": "4-5 sentences. Hook opening. What they'll discover. Emotional promise. Subscribe CTA. End with 10 hashtags including #AmbientNestHQ #{series_name.replace(' ','')}",
      "tags": ["25 tags: series name, topic keywords, mood tags, channel tags, trending terms"],
      "thumbnail_text": "3-4 words MAX for thumbnail — ultra dramatic",
      "segments": [
        {{
          "narration": "The spoken text for this segment.",
          "image_prompt": "Specific visual for AI image generation in this style: {image_style}",
          "keyword": "Pexels video search term for this segment",
          "atmosphere": "ambient | tense | shocking | melancholic | haunting | triumphant"
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
        script = json.loads(response.text.strip())
        print(f"✅ Full script: {len(script.get('segments',[]))} segments | {script.get('episode_title','')[:60]}")
        return script
    except Exception as e:
        raise RuntimeError(f"Full script generation failed: {e}")


def _generate_short_script(client, series, story, full_script):
    """Generate a 60-second Short teaser from the most gripping moment."""
    series_name = series["name"]
    image_style = series["image_style"]
    episode_title = full_script.get("episode_title", "")

    prompt = f"""
    You are creating a 60-second YouTube Short TEASER for this episode:
    Series: "{series_name}"
    Episode: "{episode_title}"
    Story: {json.dumps(story)}

    The Short must:
    - Open with the SINGLE most shocking/gripping moment from the story
    - Make viewers desperate to watch the full video
    - End with "Watch the full story on AmbientNest HQ"
    - Feel like a movie trailer, not a summary
    - Be exactly 5 scenes, each ~10-12 seconds

    Output ONE raw JSON object (no markdown):
    {{
      "short_title": "Short title under 80 chars — shock value, curiosity gap. Include #Shorts",
      "short_description": "2-3 sentences teaser. CTA to watch full video. 5 hashtags.",
      "short_tags": ["15 tags including Shorts, viral, series name"],
      "scenes": [
        {{
          "narration": "2-3 punchy sentences. Fast. Visceral. No filler.",
          "image_prompt": "Specific visual for AI generation in this style: {image_style}",
          "duration": 11
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
        script = json.loads(response.text.strip())
        print(f"✅ Short script: {script.get('short_title','')[:60]}")
        return script
    except Exception as e:
        raise RuntimeError(f"Short script generation failed: {e}")