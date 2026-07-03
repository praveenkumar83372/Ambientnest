import os
import sys
import subprocess

STREAM_KEY  = os.environ.get("YOUTUBE_STREAM_KEY")
RTMP_URL    = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
VIDEO_FILE  = "cat on window.mp4"
AUDIO_FILE  = "pulsebox-lofi.mp3"
# CHANGED: 5.4 hours (5h 24m) to completely avoid overlapping stream key collisions
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

cmd = [
    "ffmpeg",
    "-loglevel", "info",
    "-stream_loop", "-1",
    "-re",
    "-i", VIDEO_FILE,
    "-stream_loop", "-1",
    "-re",
    "-i", AUDIO_FILE,
    "-t", str(STREAM_SECS),
    "-vf", "scale=1280:720,fps=30",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-b:v", "2500k",
    "-minrate", "2500k",
    "-maxrate", "2500k",
    "-bufsize", "5000k",
    "-pix_fmt", "yuv420p",
    "-g", "60",
    "-keyint_min", "60",
    "-sc_threshold", "0",
    "-r", "30",
    "-vsync", "1",
    "-c:a", "aac",
    "-b:a", "128k",
    "-ar", "44100",
    "-ac", "2",
    "-map", "0:v:0",
    "-map", "1:a:0",
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