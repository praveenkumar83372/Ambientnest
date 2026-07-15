"""
hana_story.py
Turns (persistent state + real weather/season + daypart + optional viewer
comment) into today's story: narration, a shot list for animation, sfx cues,
and the state deltas to save afterward.

MULTI-PROVIDER FALLBACK: only 3 requests/day are needed, but free-tier quotas
are small and unpredictable, so this tries a chain of free providers in order
and falls through to the next one if a provider is missing its key, out of
quota, or errors out. As long as ONE provider in the chain has quota left,
the video still gets made.

Providers (in default order): Gemini -> Groq -> OpenRouter -> Mistral
Configure which ones run + their order via HANA_TEXT_PROVIDERS, e.g.:
    HANA_TEXT_PROVIDERS=gemini,groq,mistral
Each provider only activates if its API key env var is set; missing keys are
skipped silently (not treated as failures).

Env vars used:
    GEMINI_API_KEY       -> Gemini
    GROQ_API_KEY          -> Groq
    OPENROUTER_API_KEY    -> OpenRouter
    MISTRAL_API_KEY       -> Mistral
"""

import json
import os
import re
import sys

import requests

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


# ---------------------------------------------------------------------------
# Prompt building (provider-agnostic)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Provider implementations
# Each provider function takes (system_prompt, user_prompt) and returns raw
# text from the model. Errors (missing key, quota, HTTP failure) raise —
# the caller in generate_story() catches and moves to the next provider.
# ---------------------------------------------------------------------------

def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    import google.generativeai as genai
    model_name = os.environ.get("HANA_GEMINI_MODEL", "gemini-2.5-flash-lite")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
    response = model.generate_content(
        user_prompt,
        generation_config={"temperature": 0.9, "response_mime_type": "application/json"},
    )
    return response.text


def _call_openai_compatible(base_url: str, api_key: str, model: str,
                             system_prompt: str, user_prompt: str,
                             extra_headers: dict = None) -> str:
    """Shared caller for any OpenAI-compatible chat completions endpoint
    (Groq, OpenRouter, Mistral all implement this same shape)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.9,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60)
    if resp.status_code == 429:
        raise RuntimeError(f"rate limited (429): {resp.text[:200]}")
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_groq(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")
    model = os.environ.get("HANA_GROQ_MODEL", "llama-3.3-70b-versatile")
    return _call_openai_compatible("https://api.groq.com/openai/v1", api_key, model,
                                    system_prompt, user_prompt)


def _call_openrouter(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    # ":free" suffix models run on OpenRouter's free pool, separate quota from everything else here
    model = os.environ.get("HANA_OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
    return _call_openai_compatible(
        "https://openrouter.ai/api/v1", api_key, model, system_prompt, user_prompt,
        extra_headers={"HTTP-Referer": "https://github.com/", "X-Title": "Hana's World"},
    )


def _call_mistral(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY not set")
    model = os.environ.get("HANA_MISTRAL_MODEL", "mistral-small-latest")
    return _call_openai_compatible("https://api.mistral.ai/v1", api_key, model,
                                    system_prompt, user_prompt)


PROVIDERS = {
    "gemini": _call_gemini,
    "groq": _call_groq,
    "openrouter": _call_openrouter,
    "mistral": _call_mistral,
}

DEFAULT_PROVIDER_ORDER = ["gemini", "groq", "openrouter", "mistral"]


def _provider_order() -> list[str]:
    raw = os.environ.get("HANA_TEXT_PROVIDERS")
    if not raw:
        return DEFAULT_PROVIDER_ORDER
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_story(state: dict, context: dict, slot: str, comment: dict | None = None) -> dict:
    user_prompt = _build_user_prompt(state, context, slot, comment)
    order = _provider_order()

    errors = []
    for name in order:
        call_fn = PROVIDERS.get(name)
        if not call_fn:
            print(f"[hana_story] Unknown provider '{name}', skipping", file=sys.stderr)
            continue
        try:
            print(f"[hana_story] Trying provider: {name}")
            raw_text = call_fn(SYSTEM_PROMPT, user_prompt)
            story = _extract_json(raw_text)
            story["slot"] = slot
            story["_provider_used"] = name
            print(f"[hana_story] Success with provider: {name}")
            return story
        except Exception as e:
            msg = f"{name}: {e}"
            print(f"[hana_story] Provider failed ({msg})", file=sys.stderr)
            errors.append(msg)
            continue

    raise RuntimeError(
        "All text providers failed or were unconfigured. Tried: "
        f"{order}. Errors: {' | '.join(errors) if errors else 'no providers had keys set'}"
    )


if __name__ == "__main__":
    # quick manual smoke test — tries the full provider chain
    from hana_state import load_state
    from japan_data import get_context

    state = load_state()
    ctx = get_context(state["location"]["lat"], state["location"]["lon"])
    story = generate_story(state, ctx, ctx["daypart"])
    print(json.dumps(story, indent=2, ensure_ascii=False))
