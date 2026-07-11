"""
AmbientNest HQ — 24/7 Lo-fi Live Stream
Uses exact YouTube recommended encoder settings to fix black screen issue.
Includes filter_complex with realtime throttling to fix the encoder speed error.
"""

import os
import sys
import subprocess

STREAM_KEY  = os.environ.get("YOUTUBE_STREAM_KEY")
RTMP_URL    = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
VIDEO_FILE  = "cat on window.mp4"
AUDIO_FILE  = "pulsebox-lofi.mp3"
# Set to 5.4 hours (5h 24m) to completely avoid overlapping stream key crashes
STREAM_SECS = int(5.4 * 3600)

if not STREAM_KEY:
    print("❌ YOUTUBE_STREAM_KEY not set.")
    sys.exit(1)

if not os.path.exists(VIDEO_FILE):
    print(f"❌ Video file not found: {VIDEO_FILE}")
    sys.exit(1)

if not os.path.exists(AUDIO_FILE):
    print(f"❌ Audio file not found: {AUDIO_FILE}")
    sys.exit(1)

print("🎬 AmbientNest HQ — 24/7 Lo-fi Stream starting...")
print(f"   Streaming for {STREAM_SECS//3600}h {(STREAM_SECS%3600)//60}m")
print("🔄 Independent loops with realtime throttling enabled.")

cmd = [
    "ffmpeg",
    "-loglevel", "info",

    # 1. Standard Inputs
    "-i", VIDEO_FILE,
    "-i", AUDIO_FILE,

    # 2. Total Session Duration
    "-t", str(STREAM_SECS),

    # 3. Filter Complex: Loops files AND forces them to process at 1x real-time speed
    "-filter_complex", (
        "[0:v]loop=loop=-1:size=30000:start=0,realtime,scale=1280:720,fps=30[vloop];"
        "[1:a]aloop=loop=-1:size=2e+09:start=0,arealtime[aloop]"
    ),

    # Video settings — exact YouTube spec
    "-map", "[vloop]",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-b:v", "2500k",
    "-minrate", "2500k",
    "-maxrate", "2500k",
    "-bufsize", "5000k",
    "-pix_fmt", "yuv420p",
    "-g", "60",                    # keyframe every 2s (required by YouTube)
    "-keyint_min", "60",
    "-sc_threshold", "0",          # disable scene detection for stable keyframes
    "-r", "30",
    "-vsync", "1",                 # keep video sync stable

    # Audio settings
    "-map", "[aloop]",
    "-c:a", "aac",
    "-b:a", "128k",
    "-ar", "44100",
    "-ac", "2",

    # Output
    "-f", "flv",
    "-flvflags", "no_duration_filesize",
    RTMP_URL,
]

print("▶   Connecting to YouTube RTMP...")
try:
    subprocess.run(cmd, check=True)
    print("✅ Session complete — next cron job takes over.")
except subprocess.CalledProcessError as e:
    print(f"❌ ffmpeg error: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print("⏹   Stopped manually.")
