"""
hana_animation.py
Turns each scene dict from hana_story.py into a real animated video clip
using HuggingFace's hosted Wan2.1 (image-to-video) model, so Hana's
appearance stays consistent across every video (no static screen/pic cards —
everything is animated).

Approach:
  1. A single locked reference image of Hana (assets/character/hana_ref.png)
     defines her design.
  2. For each scene we first get a Ghibli-style KEYFRAME image (text+image ->
     image) that places Hana, in her fixed design, into today's setting.
  3. That keyframe is fed into Wan2.1 image-to-video to animate it into a
     short clip matching scene['duration_seconds'].

Requires env var HF_TOKEN. Uses huggingface_hub's InferenceClient so it
works against whichever hosted provider is available for the model.
"""

import os
import time
from pathlib import Path

from huggingface_hub import InferenceClient

CHARACTER_REF = Path(__file__).parent / "assets" / "character" / "hana_ref.png"
OUTPUT_DIR = Path(__file__).parent / "output" / "scenes"

IMAGE_MODEL = os.environ.get("HANA_IMAGE_MODEL", "black-forest-labs/FLUX.1-dev")
VIDEO_MODEL = os.environ.get("HANA_VIDEO_MODEL", "Wan-AI/Wan2.1-I2V-14B-720P")

HANA_STYLE_PREFIX = (
    "Studio Ghibli style hand-painted anime, warm cozy lighting, soft watercolor "
    "backgrounds, gentle film grain, 2D animation aesthetic. Character: Hana, "
    "19-year-old Japanese girl, [LOCKED DESIGN — see reference image], "
    "consistent hairstyle and outfit across all scenes. "
)


def _client() -> InferenceClient:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is not set")
    return InferenceClient(token=token)


def generate_keyframe(scene: dict, out_path: Path) -> Path:
    """Text(+reference image)-to-image: places Hana into this scene's setting."""
    client = _client()
    prompt = (
        f"{HANA_STYLE_PREFIX}Setting: {scene['setting']}. "
        f"Action: {scene['action']}. Vertical 9:16 composition, cinematic framing."
    )

    kwargs = {}
    if CHARACTER_REF.exists():
        kwargs["image"] = CHARACTER_REF.read_bytes()  # img2img style guidance if backend supports it

    image = client.text_to_image(prompt, model=IMAGE_MODEL, **kwargs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)
    return out_path


def animate_keyframe(keyframe_path: Path, scene: dict, out_path: Path) -> Path:
    """Image-to-video: brings the keyframe to life for this scene's duration."""
    client = _client()
    motion_prompt = f"{scene['action']}. Subtle natural motion, gentle camera drift, looping ambience."

    with open(keyframe_path, "rb") as f:
        image_bytes = f.read()

    video_bytes = client.image_to_video(
        image_bytes,
        prompt=motion_prompt,
        model=VIDEO_MODEL,
        num_frames=int(scene.get("duration_seconds", 8)) * 16,  # approx @16fps, adjust to model spec
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(video_bytes)
    return out_path


def render_scene(scene: dict, video_id: str) -> Path:
    """Full pipeline for one scene: keyframe -> animated clip. Retries lightly on transient errors."""
    scene_tag = f"{video_id}_scene{scene['scene_number']}"
    keyframe_path = OUTPUT_DIR / f"{scene_tag}_keyframe.png"
    clip_path = OUTPUT_DIR / f"{scene_tag}.mp4"

    last_err = None
    for attempt in range(3):
        try:
            generate_keyframe(scene, keyframe_path)
            animate_keyframe(keyframe_path, scene, clip_path)
            return clip_path
        except Exception as e:
            last_err = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Failed to render scene {scene['scene_number']} after 3 attempts: {last_err}")


def render_all_scenes(story: dict, video_id: str) -> list[Path]:
    return [render_scene(scene, video_id) for scene in story["scenes"]]


if __name__ == "__main__":
    print(f"Character ref exists: {CHARACTER_REF.exists()} -> {CHARACTER_REF}")
    print("This module is meant to be called from hana_world.py, not run standalone "
          "(it needs a story dict). Use it as a smoke test only to check the reference image path.")
