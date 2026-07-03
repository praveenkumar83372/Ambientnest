"""
AmbientNest HQ — 24/7 Lo-fi Live Stream
Loops pixel art video + lo-fi music and streams to YouTube via RTMP.
Runs on GitHub Actions — auto-restarts every 5h30m with overlap so
viewers never feel a gap or interruption.
"""

import os
import sys
import subprocess
from stream_meta import update_live_broadcast_metadata

# ── Config ────────────────────────────────────────────────────────────────────
STREAM_KEY  = os.environ.get("YOUTUBE_STREAM_KEY")
RTMP_URL    = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
VIDEO_FILE  = "cat on window.mp4"
AUDIO_FILE  = "pulsebox-lofi.mp3"
STREAM_SECS = int(5.75 * 3600)   # 5h45m — GitHub kills at 6h, overlap handles the gap

if not STREAM_KEY:
    print("❌ YOUTUBE_STREAM_KEY not set. Add it to GitHub Secrets.")
    sys.exit(1)

if not os.path.exists(VIDEO_FILE):
    print(f"❌ Video file not found: {VIDEO_FILE}")
    sys.exit(1)

if not os.path.exists(AUDIO_FILE):
    print(f"❌ Audio file not found: {AUDIO_FILE}")
    sys.exit(1)

print("🎬 AmbientNest HQ — 24/7 Lo-fi Stream starting...")
print(f"   Video : {VIDEO_FILE}")
print(f"   Audio : {AUDIO_FILE}")
print(f"   Duration this session: {STREAM_SECS//3600}h {(STREAM_SECS%3600)//60}m")
print(f"   Next restart: auto via GitHub Actions cron")

# ── Update YouTube live title + description + tags ────────────────────────────
print("\n📝 Updating live broadcast metadata...")
update_live_broadcast_metadata()

# ── ffmpeg stream command ─────────────────────────────────────────────────────
cmd = [
    "ffmpeg",
    "-loglevel", "warning",
    # Loop both inputs infinitely BEFORE reading — guarantees no early stop
    "-stream_loop", "-1",
    "-re",
    "-i", VIDEO_FILE,
    "-stream_loop", "-1",
    "-i", AUDIO_FILE,
    "-t", str(STREAM_SECS),

    # Video: 1280x720, 30fps, h264, 2500kbps
    "-vf", "scale=1280:720",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-tune", "stillimage",         # optimized for looping animation/still content
    "-b:v", "2500k",
    "-maxrate", "2500k",
    "-bufsize", "5000k",
    "-pix_fmt", "yuv420p",
    "-g", "60",                    # keyframe every 2s at 30fps
    "-r", "30",

    # Audio: aac 128kbps stereo from lofi mp3
    "-c:a", "aac",
    "-b:a", "128k",
    "-ar", "44100",
    "-ac", "2",

    # Map: video from file 0, audio from file 1
    "-map", "0:v:0",
    "-map", "1:a:0",

    # Output to YouTube RTMP
    "-f", "flv",
    RTMP_URL,
]

print("\n▶  Streaming to YouTube RTMP...")
try:
    subprocess.run(cmd, check=True)
    print("\n✅ Session ended — next cron job already overlapping. No viewer gap.")
except subprocess.CalledProcessError as e:
    print(f"\n❌ ffmpeg error: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n⏹  Stream manually stopped.")