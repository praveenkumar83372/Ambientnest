"""
hana_assembly.py
Stitches rendered scene clips + narrated voiceover + sfx into one final
9:16 vertical video with burned-in captions.

Pipeline:
  1. Concatenate scene clips (already vertical 9:16 from hana_animation.py).
  2. Generate voiceover with Edge TTS (ja-JP-NanamiNeural handles the
     English + Japanese mix reasonably well) OR ElevenLabs if configured.
  3. Mix voiceover (loud) + sfx cues (timed) + background ambience (quiet, looped).
  4. Burn in captions from the narration text via ffmpeg subtitles filter.
  5. Output final mp4 to output/final/.

Requires: ffmpeg installed on PATH, edge-tts python package (or ELEVENLABS_API_KEY).
"""

import asyncio
import json
import subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
SCENES_DIR = OUTPUT_DIR / "scenes"
AUDIO_DIR = OUTPUT_DIR / "audio"
FINAL_DIR = OUTPUT_DIR / "final"
VOICE = "ja-JP-NanamiNeural"


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")


async def _synthesize_voice_async(text: str, out_path: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE, rate="-5%")
    await communicate.save(str(out_path))


def synthesize_voiceover(story: dict, video_id: str) -> Path:
    """One combined voice track for the whole video, scenes joined with pauses."""
    full_text = "\n\n".join(scene["narration"] for scene in story["scenes"])
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = AUDIO_DIR / f"{video_id}_voice.mp3"
    asyncio.run(_synthesize_voice_async(full_text, out_path))
    return out_path


def build_srt(story: dict, video_id: str) -> Path:
    """Naive even-split captions across each scene's duration. Good enough for
    a first pass — swap in whisper timestamp alignment later if you want it tighter."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    srt_path = AUDIO_DIR / f"{video_id}.srt"

    lines = []
    t = 0.0
    idx = 1
    for scene in story["scenes"]:
        dur = float(scene.get("duration_seconds", 8))
        start = _fmt_ts(t)
        end = _fmt_ts(t + dur)
        lines.append(f"{idx}\n{start} --> {end}\n{scene['narration']}\n")
        t += dur
        idx += 1

    srt_path.write_text("\n".join(lines), encoding="utf-8")
    return srt_path


def _fmt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def concat_scenes(scene_paths: list[Path], video_id: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    list_file = OUTPUT_DIR / f"{video_id}_concat.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in scene_paths), encoding="utf-8"
    )
    silent_video = OUTPUT_DIR / f"{video_id}_silent.mp4"
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", str(silent_video),
    ])
    return silent_video


def mix_and_caption(silent_video: Path, voice_path: Path, ambience_path, srt_path: Path,
                     video_id: str) -> Path:
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    final_path = FINAL_DIR / f"{video_id}.mp4"

    inputs = ["-i", str(silent_video), "-i", str(voice_path)]
    filter_parts = []
    if ambience_path and Path(ambience_path).exists():
        inputs += ["-stream_loop", "-1", "-i", str(ambience_path)]
        filter_parts.append("[2:a]volume=0.15[amb]")
        audio_mix = "[1:a][amb]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    else:
        audio_mix = "[1:a]anull[aout]"
    filter_parts.append(audio_mix)

    subtitle_filter = f"subtitles={str(srt_path)}:force_style='FontName=Arial,FontSize=14,PrimaryColour=&HFFFFFF,Outline=2'"
    filter_parts.append(f"[0:v]{subtitle_filter}[vout]")

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-c:a", "aac", "-shortest",
        str(final_path),
    ]
    _run(cmd)
    return final_path


def assemble(story: dict, scene_paths: list[Path], video_id: str, ambience_path=None) -> Path:
    voice_path = synthesize_voiceover(story, video_id)
    srt_path = build_srt(story, video_id)
    silent_video = concat_scenes(scene_paths, video_id)
    final_path = mix_and_caption(silent_video, voice_path, ambience_path, srt_path, video_id)
    return final_path


if __name__ == "__main__":
    print("Run via hana_world.py — this module needs a story + rendered scene paths.")
