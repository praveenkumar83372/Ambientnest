"""
Financial Sound Effects (SFX) & Audio Manager
Handles transition whooshes, cash chimes, glitch impacts, and dark ambient soundscape mixing.
Downloads and caches sounds locally via Freesound API.
"""

import os
import json
import random
import subprocess
import requests
import shutil as _shutil

def _find_ffmpeg():
    f = _shutil.which("ffmpeg")
    if f:
        return f
    # Common fallback path for local Windows development
    fallback_paths = [r"C:\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"]
    for p in fallback_paths:
        if os.path.exists(p):
            return p
    return "ffmpeg"

FFMPEG = _find_ffmpeg()

SFX_DIR = "finance_sfx"
SFX_CACHE = os.path.join(SFX_DIR, "cache.json")

# Specialized High-RPM Financial Sound Effect Library
SFX_LIBRARY = {
    "cash_register": {"query": "cash register cha ching sound", "scenes": ["money", "profit", "wealth", "cash"]},
    "coin_drop": {"query": "coins falling metal sound effect", "scenes": ["investing", "coins", "gold", "savings"]},
    "fast_whoosh": {"query": "cinematic fast whoosh transition", "scenes": ["transition", "cut", "fast", "3sec"]},
    "glitch_impact": {"query": "glitch sound impact cinematic", "scenes": ["dark", "secret", "psychology", "shock"]},
    "deep_bass_drop": {"query": "deep bass drop cinematic hit", "scenes": ["hook", "warning", "attention", "reveal"]},
    "keyboard_typing": {"query": "mechanical keyboard fast typing", "scenes": ["data", "code", "chart", "computer"]},
    "subtle_riser": {"query": "cinematic riser tension build up", "scenes": ["suspense", "rule", "breakdown", "story"]}
}


def ensure_dir():
    os.makedirs(SFX_DIR, exist_ok=True)


def load_cache():
    if os.path.exists(SFX_CACHE):
        try:
            with open(SFX_CACHE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache):
    with open(SFX_CACHE, "w") as f:
        json.dump(cache, f, indent=2)


def download_sfx(sfx_key, api_key):
    """Downloads royalty-free sound effect from Freesound API and caches locally."""
    ensure_dir()
    cache = load_cache()

    if sfx_key in cache and os.path.exists(cache[sfx_key]):
        return cache[sfx_key]

    if not api_key:
        print(f"⚠️ FREESOUND_API_KEY missing. Skipping SFX download for '{sfx_key}'.")
        return None

    info = SFX_LIBRARY.get(sfx_key)
    if not info:
        return None

    url = (
        f"https://freesound.org/apiv2/search/text/"
        f"?query={requests.utils.quote(info['query'])}"
        f"&fields=id,name,previews,duration"
        f"&token={api_key}&page_size=5"
    )

    try:
        res = requests.get(url, timeout=20).json()
        results = [r for r in (res.get("results") or []) if 0.3 < r.get("duration", 0) < 5.0]
        
        if not results:
            return None

        track = random.choice(results)
        path = os.path.join(SFX_DIR, f"{sfx_key}.mp3")

        preview_url = track["previews"].get("preview-hq-mp3") or track["previews"].get("preview-lq-mp3")
        if preview_url:
            audio_data = requests.get(preview_url, timeout=20).content
            with open(path, "wb") as f:
                f.write(audio_data)

            cache[sfx_key] = path
            save_cache(cache)
            print(f" 🔊 Downloaded SFX: {sfx_key}")
            return path

    except Exception as e:
        print(f" ⚠️ SFX fetch failed for '{sfx_key}': {e}")
        return None


def get_sfx_for_scene(scene_keywords, api_key):
    """Finds and downloads matching sound effects for scene transitions or key moments."""
    result_paths = []
    
    # Always include a fast whoosh for the 3-second scene transition
    transition_sfx = download_sfx("fast_whoosh", api_key)
    if transition_sfx:
        result_paths.append(transition_sfx)

    # Contextual sound effects matching scene tags
    for kw in (scene_keywords or []):
        matched_key = None
        for key, info in SFX_LIBRARY.items():
            if any(s_tag in str(kw).lower() for s_tag in info["scenes"]):
                matched_key = key
                break
        
        if matched_key:
            sfx_path = download_sfx(matched_key, api_key)
            if sfx_path and sfx_path not in result_paths:
                result_paths.append(sfx_path)

    return result_paths


def mix_sfx_into_scene(video_path, sfx_paths, output_path, vol=0.35):
    """
    Uses FFmpeg to layer sound effects into a scene video clip.
    Adjusts volume so narration and background music remain clearly audible.
    """
    if not sfx_paths or not os.path.exists(video_path):
        if os.path.exists(video_path):
            _shutil.copy(video_path, output_path)
        return

    inputs = ["-i", video_path]
    for p in sfx_paths:
        inputs += ["-i", p]

    n = len(sfx_paths)
    if n == 1:
        fc = f"[1:a]volume={vol}[sfx];[0:a][sfx]amix=inputs=2:duration=first[aout]"
    else:
        parts = "".join(f"[{i+1}:a]volume={vol}[s{i}];" for i in range(n))
        mix_inputs = "".join(f"[s{i}]" for i in range(n))
        fc = f"{parts}{mix_inputs}amix=inputs={n}:duration=first[sfx];[0:a][sfx]amix=inputs=2:duration=first[aout]"

    cmd = [
        FFMPEG, "-y", *inputs,
        "-filter_complex", fc,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest", output_path
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"⚠️ FFmpeg SFX mix warning (falling back to raw clip): {result.stderr.decode('utf-8', errors='ignore')[:100]}")
        _shutil.copy(video_path, output_path)


if __name__ == "__main__":
    freesound_key = os.getenv("FREESOUND_API_KEY")
    sfx = get_sfx_for_scene(["cash", "dark secret"], freesound_key)
    print(f"SFX paths fetched: {sfx}")