"""
hana_animation.py
Turns each scene dict from hana_story.py into a real animated video clip
using HuggingFace's hosted image + video models, so Hana's appearance stays
consistent across every video (no static screen/pic cards — everything is
animated).

Approach:
  1. A single locked reference image of Hana (assets/character/hana_ref.png)
     defines her design.
  2. For each scene we generate a Ghibli-style KEYFRAME image:
       - If a reference image exists, use image_to_image() to place Hana
         (in her fixed design) into today's setting, guided by the reference.
       - Otherwise, fall back to text_to_image() alone.
  3. That keyframe is fed into image_to_video() to animate it into a short
     clip.

Requires env var HF_TOKEN. Uses huggingface_hub's InferenceClient.

NOTE: huggingface_hub's inference API has changed shape a few times as HF
moved to a third-party "Inference Providers" model — this file targets the
current (2026) client, where:
  - text_to_image(prompt, model=...) takes NO image argument
  - image_to_image(image, prompt=..., model=...) is the separate img2img call
  - image_to_video(image, model=..., prompt=...) is the separate i2v call
If HF changes these signatures again, that's where to look first.
"""

import os
import time
from pathlib import Path

from huggingface_hub import InferenceClient

CHARACTER_REF = Path(__file__).parent / "assets" / "character" / "hana_ref.png"
OUTPUT_DIR = Path(__file__).parent / "output" / "scenes"

# Plain text-to-image model, used only if no reference image exists yet
IMAGE_MODEL = os.environ.get("HANA_IMAGE_MODEL", "black-forest-labs/FLUX.1-dev")
# Image-editing/img2img model, used to place Hana's locked design into each scene
IMAGE_EDIT_MODEL = os.environ.get("HANA_IMAGE_EDIT_MODEL", "black-forest-labs/FLUX.1-Kontext-dev")
# Image-to-video model — HF's officially supported I2V model as of the current client
VIDEO_MODEL = os.environ.get("HANA_VIDEO_MODEL", "Wan-AI/Wan2.2-I2V-A14B")

HANA_STYLE_PREFIX = (
    "Studio Ghibli style hand-painted anime, warm cozy lighting, soft watercolor "
    "backgrounds, gentle film grain, 2D animation aesthetic. Character: Hana, "
    "19-year-old Japanese girl, keep her exact hairstyle, outfit, and face "
    "consistent with the reference image. "
)


def _client() -> InferenceClient:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is not set")
    return InferenceClient(api_key=token)


def generate_keyframe(scene: dict, out_path: Path) -> Path:
    """Produces this scene's keyframe image. Uses image_to_image (with Hana's
    locked reference) when available, otherwise falls back to plain text_to_image."""
    client = _client()
    prompt = (
        f"{HANA_STYLE_PREFIX}Setting: {scene['setting']}. "
        f"Action: {scene['action']}. Vertical 9:16 composition, cinematic framing."
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if CHARACTER_REF.exists():
        image = client.image_to_image(
            CHARACTER_REF.read_bytes(),
            prompt=prompt,
            model=IMAGE_EDIT_MODEL,
        )
    else:
        image = client.text_to_image(prompt, model=IMAGE_MODEL)

    image.save(out_path)
    return out_path


def animate_keyframe(keyframe_path: Path, scene: dict, out_path: Path) -> Path:
    """Image-to-video: brings the keyframe to life for this scene."""
    client = _client()
    motion_prompt = f"{scene['action']}. Subtle natural motion, gentle camera drift, looping ambience."

    video_bytes = client.image_to_video(
        keyframe_path.read_bytes(),
        model=VIDEO_MODEL,
        prompt=motion_prompt,
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
            print(f"[hana_animation] Scene {scene['scene_number']} attempt {attempt + 1} failed: {e}")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Failed to render scene {scene['scene_number']} after 3 attempts: {last_err}")


def render_all_scenes(story: dict, video_id: str) -> list[Path]:
    return [render_scene(scene, video_id) for scene in story["scenes"]]


if __name__ == "__main__":
    print(f"Character ref exists: {CHARACTER_REF.exists()} -> {CHARACTER_REF}")
    print("This module is meant to be called from hana_world.py, not run standalone "
          "(it needs a story dict). Use it as a smoke test only to check the reference image path.")
