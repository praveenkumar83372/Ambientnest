"""
Updates the live broadcast title, description, and tags on YouTube
each time the stream restarts. Keeps content feeling fresh and SEO-optimized.
"""

import os
import re
import pickle
import datetime
from googleapiclient.discovery import build


def get_stream_metadata():
    """Generate dynamic title, description and tags based on time of day."""
    hour = datetime.datetime.utcnow().hour

    # Time-based title variation
    if 0 <= hour < 6:
        mood = "Late Night Lo-fi"
        vibe = "Study & Relax at 3AM 🌙"
        emoji = "🌙"
    elif 6 <= hour < 12:
        mood = "Morning Lo-fi"
        vibe = "Start Your Day Right ☀️"
        emoji = "☀️"
    elif 12 <= hour < 17:
        mood = "Afternoon Lo-fi"
        vibe = "Focus & Productivity 🎯"
        emoji = "🎯"
    elif 17 <= hour < 21:
        mood = "Evening Lo-fi"
        vibe = "Unwind & Decompress 🌆"
        emoji = "🌆"
    else:
        mood = "Night Lo-fi"
        vibe = "Chill & Sleep 🌃"
        emoji = "🌃"

    title = f"{emoji} {mood} Hip Hop — {vibe} | AmbientNest HQ 24/7 Live"

    description = f"""🎵 Welcome to AmbientNest HQ's 24/7 Lo-fi Live Stream!

The perfect background music for studying, working, relaxing, or sleeping.
Cozy pixel art visuals with chilled lo-fi beats — playing non-stop, all day, every day.

{emoji} Current Vibe: {vibe}

━━━━━━━━━━━━━━━━━━━━━━
📌 What is AmbientNest HQ?
We cover Finance, AI, History, Science, Travel, Psychology and fascinating world stories — uploaded 5 times daily. Subscribe and never miss a story.
━━━━━━━━━━━━━━━━━━━━━━

🔔 Subscribe for daily world stories + this 24/7 stream
👍 Like if the music helps you focus
💬 Drop a comment — where are you listening from?

#lofi #lofihiphop #studymusic #chillmusic #focusmusic #relaxingmusic #lofistudy #ambientnesthq #24_7lofi #lofichill #studywithme #workwithme #lofibeats #lofigirl #chilledcow #lofimix #backgroundmusic #lofisongs #studymusic2026 #chillvibes"""

    tags = [
        "lofi", "lofi hip hop", "study music", "chill music", "focus music",
        "relaxing music", "lofi study", "AmbientNestHQ", "24/7 lofi",
        "lofi chill", "study with me", "work with me", "lofi beats",
        "background music", "lofi songs", "chill vibes", "lofi live",
        "lofi stream", "chill beats", "ambient music", "sleep music",
        "concentration music", "deep focus", "lofi radio", "pixel art lofi",
    ]

    return title, description, tags


def _clean_tags(tags):
    clean, total = [], 0
    for t in tags:
        t = re.sub(r"[^a-zA-Z0-9 \-/]", "", str(t)).strip()
        if not t or len(t) > 30 or total + len(t) > 490:
            continue
        clean.append(t)
        total += len(t) + 1
    return clean


def update_live_broadcast_metadata():
    """Find the active live broadcast and update its title, description, tags."""
    if not os.path.exists("token.pickle"):
        print("⚠️   token.pickle not found — skipping metadata update.")
        return

    with open("token.pickle", "rb") as f:
        creds = pickle.load(f)

    youtube = build("youtube", "v3", credentials=creds)
    title, description, tags = get_stream_metadata()

    try:
        # UPDATED: Use broadcastStatus="all" to reliably target the persistent panel stream reference
        broadcasts = youtube.liveBroadcasts().list(
            part="id,snippet,status",
            broadcastStatus="all",
            maxResults=5,
        ).execute()

        items = broadcasts.get("items", [])

        if not items:
            print("⚠️   No active or upcoming broadcast found to update.")
            print(f"   Stream title would be: {title}")
            return

        # Target the primary streaming frame entry
        broadcast_id = items[0]["id"]

        # Update the broadcast metadata
        youtube.liveBroadcasts().update(
            part="snippet",
            body={
                "id": broadcast_id,
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "scheduledStartTime": items[0]["snippet"]["scheduledStartTime"],
                },
            },
        ).execute()

        # Update tags via video update
        youtube.videos().update(
            part="snippet",
            body={
                "id": broadcast_id,
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "tags": _clean_tags(tags),
                    "categoryId": "10",  # Music category
                },
            },
        ).execute()

        print(f"✅ Live broadcast metadata updated! ID: {broadcast_id}")
        print(f"   Title: {title}")

    except Exception as e:
        print(f"⚠️   Metadata update failed: {e}")
        print("   Stream will continue — just without updated title.")


if __name__ == "__main__":
    update_live_broadcast_metadata()