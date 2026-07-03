"""
AmbientNest HQ — 24/7 Lo-fi Live Stream
Uses exact YouTube recommended encoder settings to fix black screen issue.
Includes the -re flag to enforce stable, real-time live broadcasting.
"""

import os
import sys
import subprocess

STREAM_KEY  = os.environ.get("YOUTUBE_STREAM_KEY")
RTMP_URL    = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
VIDEO_FILE  = "cat on window.mp4"
AUDIO_FILE  = "pulsebox-lofi.mp3"
STREAM_SECS = int(5.75 * 3600)

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

# YouTube exact recommended settings:
# Video: H.264, 1280x720, 30fps, 2500kbps, yuv420p
# Audio: AAC, 128kbps, 44100Hz, stereo
# Format: FLV to RTMP

cmd = [
    "ffmpeg",
    "-loglevel", "info",           # show more info to debug if needed

    # CRITICAL FIX: Force real-time streaming speed (1s of video per 1s of clock time)
    "-re", 

    # Loop video input
    "-stream_loop", "-1",
    "-i", VIDEO_FILE,

    # Loop audio input  
    "-stream_loop", "-1",
    "-i", AUDIO_FILE,

    # Stop after session duration
    "-t", str(STREAM_SECS),

    # Video settings — exact YouTube spec
    "-vf", "scale=1280:720,fps=30",  # force exact 30fps
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
    "-c:a", "aac",
    "-b:a", "128k",
    "-ar", "44100",
    "-ac", "2",

    # Map video from file 0, audio from file 1
    "-map", "0:v:0",
    "-map", "1:a:0",

    # Output
    "-f", "flv",
    "-flvflags", "no_duration_filesize",  # required for live streaming
    RTMP_URL,
]

print("▶  Connecting to YouTube RTMP...")
try:
    subprocess.run(cmd, check=True)
    print("✅ Session complete — next cron job takes over.")
except subprocess.CalledProcessError as e:
    print(f"❌ ffmpeg error: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print("⏹  Stopped manually.")