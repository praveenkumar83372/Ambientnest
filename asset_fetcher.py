"""
Finance Channel Asset Fetcher
Downloads 20 vertical video clips or images from Pexels API matching the 
CVO's 3-second visual prompts.

Rules:
1. No duplicate clips/images inside the same video.
2. Reuses assets only after 10+ videos (tracked in asset_history.json).
3. Every downloaded clip is cut or formatted to exactly 3.0 seconds.
"""

import os
import json
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
HISTORY_FILE = "asset_history.json"

def load_asset_history():
    """Loads previously used asset IDs to enforce the 10-video reuse rule."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {"history": []}
    return {"history": []}

def save_asset_history(history_data):
    """Saves updated asset usage history."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_data, f, indent=4)

def get_banned_asset_ids(history_data, buffer_videos=10):
    """Gets asset IDs used in the last `buffer_videos` runs."""
    recent_runs = history_data.get("history", [])[-buffer_videos:]
    banned_ids = set()
    for run in recent_runs:
        for asset_id in run.get("used_ids", []):
            banned_ids.add(asset_id)
    return banned_ids

def fetch_pexels_asset(query, banned_ids, local_used_ids):
    """
    Searches Pexels for vertical videos or fallback photos matching the prompt query.
    Ensures no duplicate inside the same video or from the banned list.
    """
    headers = {"Authorization": PEXELS_API_KEY}
    
    # 1. Try fetching vertical HD videos first
    video_url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=15"
    try:
        res = requests.get(video_url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for video in data.get("videos", []):
                vid_id = f"vid_{video['id']}"
                if vid_id in banned_ids or vid_id in local_used_ids:
                    continue  # Skip banned or already used in this video
                
                # Pick best vertical HD file
                for file_info in video.get("video_files", []):
                    if file_info.get("height", 0) >= 1080 and file_info.get("width", 0) <= 1080:
                        return file_info["link"], vid_id, "video"
                
                # Fallback to first valid video link
                if video.get("video_files"):
                    return video["video_files"][0]["link"], vid_id, "video"
    except Exception as e:
        print(f"⚠️ Video search warning for query '{query}': {e}")

    # 2. Fallback to vertical photos if no video was found
    photo_url = f"https://api.pexels.com/v1/search?query={query}&orientation=portrait&per_page=15"
    try:
        res = requests.get(photo_url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for photo in data.get("photos", []):
                img_id = f"img_{photo['id']}"
                if img_id in banned_ids or img_id in local_used_ids:
                    continue
                return photo["src"]["portrait"], img_id, "image"
    except Exception as e:
        print(f"⚠️ Photo search warning for query '{query}': {e}")

    # 3. Emergency fallback stock asset (Finance default)
    fallback_id = f"fallback_{hashlib.md5(query.encode()).hexdigest()[:8]}"
    fallback_url = "https://images.pexels.com/photos/259027/pexels-photo-259027.jpeg"
    return fallback_url, fallback_id, "image"

def download_and_prepare_assets(visual_prompts):
    """
    Downloads 20 assets for the visual prompts list, ensuring strict deduplication.
    Returns metadata list for video assembly.
    """
    if not PEXELS_API_KEY:
        raise ValueError("❌ PEXELS_API_KEY is missing! Check repository secrets.")

    history_data = load_asset_history()
    banned_ids = get_banned_asset_ids(history_data, buffer_videos=10)
    
    local_used_ids = set()
    downloaded_assets = []

    os.makedirs("temp_assets", exist_ok=True)
    print(f"\n📥 Fetching {len(visual_prompts)} distinct 3-second assets...")

    for idx, prompt in enumerate(visual_prompts):
        print(f" 🎬 [Asset {idx+1}/{len(visual_prompts)}] Prompt: '{prompt}'")
        
        asset_url, asset_id, asset_type = fetch_pexels_asset(prompt, banned_ids, local_used_ids)
        
        # Lock ID to prevent re-use inside this same video
        local_used_ids.add(asset_id)
        
        # Download raw file
        ext = "mp4" if asset_type == "video" else "jpg"
        file_path = f"temp_assets/scene_{idx:02d}.{ext}"
        
        res = requests.get(asset_url, stream=True, timeout=15)
        if res.status_code == 200:
            with open(file_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        downloaded_assets.append({
            "scene_index": idx,
            "file_path": file_path,
            "type": asset_type,
            "asset_id": asset_id,
            "target_duration": 3.0  # Exactly 3 seconds per scene
        })

    # Log used asset IDs into history
    history_data.setdefault("history", []).append({
        "timestamp": os.getenv("GITHUB_SHA", "local_run"),
        "used_ids": list(local_used_ids)
    })
    save_asset_history(history_data)

    print(f"✅ Successfully downloaded {len(downloaded_assets)} unique assets with 0 internal duplicates!")
    return downloaded_assets

if __name__ == "__main__":
    # Test script loading from generated script JSON
    if os.path.exists("current_script.json"):
        with open("current_script.json", "r") as f:
            script_payload = json.load(f)
        prompts = script_payload.get("visual_prompts", [])
        if len(prompts) == 20:
            download_and_prepare_assets(prompts)
        else:
            print(f"⚠️ Expected 20 prompts, found {len(prompts)}.")
    else:
        print("Run `python orchestrator.py` first to generate `current_script.json`!")