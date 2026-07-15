"""
hana_story.py
Turns (persistent state + real weather/season + daypart + optional viewer
comment) into today's story: narration, a shot list for animation, sfx cues,
and the state deltas to save afterward.

Uses Gemini (as originally planned) via the google-generativeai SDK.
Requires env var GEMINI_API_KEY.
"""

import json
import os
import re

import google.generativeai as genai

MODEL_NAME = os.environ.get("HANA_TEXT_MODEL", "gemini-2.0-flash")

SYSTEM_PROMPT = """You are the story-writer for "Hana's World", a Studio Ghibli-style
animated daily-life series about Hana, a 19-year-old girl living alone in a small
coastal town in Japan. Her life is real and continuous: what happened yesterday
matters today. She is NOT episodic content — she is a living person whose memory
persists.

Voice: warm, soft, gently paced, like a Ghibli film. Narration is in English with
natural Japanese words woven in occasionally (hai, ne, arigatou, ohayou, itadakimasu,
tadaima, etc.) — never full Japanese sentences, just seasoning, and always followed
by enough context that an English-only viewer understands.

Hana shows REAL emotions — sometimes sad, sometimes frustrated, sometimes overjoyed.
Do not sanitize her feelings into constant cheerfulness.

She is alone (no recurring side characters yet) but she talks to herself, to plants,
to her pottery, to the cat that sometimes crosses her path.

Format: vertical short (9:16), roughly 45-75 seconds spoken, 3-6 scenes.

Return ONLY valid JSON, no markdown fences, no commentary, matching this schema:

{
  "title": "short YouTube title, under 60 chars",
  "slot": "morning|midday|evening",
  "narration_summary": "1-2 sentence summary of what happens in THIS video, for memory",
  "emotional_state_after": "short phrase describing Hana's mood at the end of this video",
  "scenes": [
    {
      "scene_number": 1,
      "setting": "visual description of location/lighting/season for the animator",
      "action": "what Hana physically does in this scene",
      "narration": "the English (+ light Japanese) narration line(s) spoken during this scene",
      "sfx": ["birdsong", "kettle boiling"],
      "duration_seconds": 10
    }
  ],
  "state_updates": {
    "garden": {"tomatoes": "..."},
    "landmarks": {"cherry_tree_on_the_hill": "..."},
    "ongoing_projects": [{"name": "pottery", "status": "...", "days_in": 6}],
    "kyoto_yen_delta": 0
  },
  "comment_response": "if a viewer comment was provided, 1 short line where Hana reacts to it naturally in the story, else null"
}
"""


def _build_user_prompt(state: dict, context: dict, slot: str, comment: dict | None) -> str:
    parts = [
        f"TODAY: {context['date']} ({context['weekday']}), {context['season']}, video slot = {slot}.",
        f"WEATHER: {context['weather']['description']}, "
        f"{context['weather'].get('temp_c')}C (range "
        f"{context['weather'].get('temp_min_c')}-{context['weather'].get('temp_max_c')}C), "
        f"humidity {context['weather'].get('humidity')}%.",
        f"DAY COUNT: this is day {state['day_count']} of Hana's life on camera.",
        f"HANA: {state['hana']['personality']}. Lives: {state['hana']['home']}.",
        f"CURRENT EMOTIONAL STATE (carry this forward, don't reset it): {state['emotional_state']}.",
        f"WEATHER YESTERDAY: {state.get('weather_yesterday')}.",
        f"ONGOING PROJECTS: {json.dumps(state['ongoing_projects'], ensure_ascii=False)}",
        f"GARDEN: {json.dumps(state['garden'], ensure_ascii=False)}",
        f"LANDMARKS: {json.dumps(state['landmarks'], ensure_ascii=False)}",
        f"RECENT EVENTS (most recent first): {json.dumps(state['recent_events'], ensure_ascii=False)}",
        f"EARLIER TODAY: {json.dumps(state.get('day_log_today', []), ensure_ascii=False)}",
    ]
    if comment:
        parts.append(
            f"A VIEWER COMMENT to weave into today's story naturally (from {comment['from']}): "
            f"\"{comment['text']}\""
        )
    parts.append(
        "Write the NEXT chapter of Hana's continuous life — do not restart her story, "
        "continue it. Respect the season and weather. Keep at least one ongoing project "
        "moving forward (even a small step), unless today's story is about something new."
    )
    return "\n".join(parts)


def _extract_json(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def generate_story(state: dict, context: dict, slot: str, comment: dict | None = None) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_PROMPT)

    user_prompt = _build_user_prompt(state, context, slot, comment)
    response = model.generate_content(
        user_prompt,
        generation_config={"temperature": 0.9, "response_mime_type": "application/json"},
    )

    story = _extract_json(response.text)
    story["slot"] = slot
    return story


if __name__ == "__main__":
    # quick manual smoke test (requires GEMINI_API_KEY)
    from hana_state import load_state
    from japan_data import get_context

    state = load_state()
    ctx = get_context(state["location"]["lat"], state["location"]["lon"])
    story = generate_story(state, ctx, ctx["daypart"])
    print(json.dumps(story, indent=2, ensure_ascii=False))
