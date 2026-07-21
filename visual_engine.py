"""
Financial Visual Engine
Processes downloaded 3-second stock video clips and static images.
Standardizes resolution to 1080x1920 (9:16 portrait) and applies smooth 
Ken Burns zoom effects to static photos for high visual retention.
"""

import os
import shutil as _shutil
from PIL import Image, ImageDraw, ImageFont

# MoviePy v1 vs v2 compatibility handler
try:
    from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
except ImportError:
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip


def _find_ffmpeg():
    f = _shutil.which("ffmpeg")
    if f:
        return f
    fallback_paths = [r"C:\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"]
    for p in fallback_paths:
        if os.path.exists(p):
            return p
    return "ffmpeg"


FFMPEG = _find_ffmpeg()


def create_placeholder_image(output_path, text="Financial Secret"):
    """Generates an aesthetic dark-themed financial fallback image if an asset download fails."""
    img = Image.new("RGB", (1080, 1920), color=(15, 23, 42))  # Dark slate background
    draw = ImageDraw.Draw(img)

    # Accent container box
    draw.rectangle([50, 800, 1030, 1120], fill=(30, 41, 59), outline=(234, 179, 8), width=3)

    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except Exception:
        font = ImageFont.load_default()

    draw.text((540, 960), text, fill=(255, 255, 255), font=font, anchor="mm")
    img.save(output_path)
    return output_path


def apply_ken_burns_effect(image_path, duration=3.0, target_size=(1080, 1920)):
    """
    Applies a smooth dynamic zoom-in (Ken Burns) effect to static photos.
    Prevents still images from feeling flat and boosts viewer retention.
    """
    img_clip = ImageClip(image_path).set_duration(duration)

    # Scale to fill height 1920
    img_clip = img_clip.resize(height=target_size[1])
    if img_clip.w < target_size[0]:
        img_clip = img_clip.resize(width=target_size[0])

    # Crop center to exactly 1080x1920
    img_clip = img_clip.crop(x_center=img_clip.w / 2, y_center=img_clip.h / 2, width=1080, height=1920)

    # Dynamic zoom function: scales smoothly from 1.0 to 1.15 over duration
    def zoom_func(t):
        return 1.0 + 0.05 * t

    zoomed_clip = img_clip.resize(zoom_func)

    # Re-crop to lock bounding box at 1080x1920
    final_clip = CompositeVideoClip([zoomed_clip.set_position("center")], size=target_size).set_duration(duration)
    return final_clip


def process_scene_asset(asset_info, output_dir="temp_processed"):
    """
    Processes a single raw visual asset (video clip or photo) into a 
    standardized 3.0-second 1080x1920 vertical clip.
    """
    os.makedirs(output_dir, exist_ok=True)
    raw_path = asset_info["file_path"]
    asset_type = asset_info["type"]
    idx = asset_info["scene_index"]
    target_duration = asset_info.get("target_duration", 3.0)

    output_path = os.path.join(output_dir, f"scene_processed_{idx:02d}.mp4")

    print(f" 🎬 [Visual Engine] Processing Scene {idx+1} ({asset_type.upper()})...")

    try:
        if asset_type == "video" and os.path.exists(raw_path):
            # Load raw video clip and trim to exactly 3.0 seconds
            clip = VideoFileClip(raw_path)

            # Subclip to 3 seconds (or loop if shorter than 3s)
            if clip.duration < target_duration:
                clip = clip.loop(duration=target_duration)
            else:
                clip = clip.subclip(0, target_duration)

            # Format to 1080x1920 portrait
            clip = clip.resize(height=1920)
            if clip.w > 1080:
                clip = clip.crop(x_center=clip.w / 2, width=1080)
            elif clip.w < 1080:
                clip = clip.resize(width=1080)

            # Render processed clip clip
            clip.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio=False,
                preset="ultrafast",
                logger=None
            )
            clip.close()

        else:
            # Static photo processing with Ken Burns zoom effect
            if not os.path.exists(raw_path):
                raw_path = create_placeholder_image(f"temp_placeholder_{idx}.jpg")

            clip = apply_ken_burns_effect(raw_path, duration=target_duration)
            clip.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio=False,
                preset="ultrafast",
                logger=None
            )
            clip.close()

        return output_path

    except Exception as e:
        print(f"⚠️ Error processing scene asset {idx}: {e}. Creating fallback scene.")
        fallback_path = create_placeholder_image(f"temp_fallback_{idx}.jpg")
        clip = apply_ken_burns_effect(fallback_path, duration=target_duration)
        clip.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio=False,
            preset="ultrafast",
            logger=None
        )
        clip.close()
        return output_path


def process_all_visual_assets(asset_list):
    """Loops through all downloaded assets (20 scenes) and processes them sequentially."""
    print(f"\n🖼️ [Visual Engine] Processing {len(asset_list)} visual scenes into 3.0s 1080x1920 clips...")
    processed_paths = []

    for asset in asset_list:
        out_path = process_scene_asset(asset)
        processed_paths.append(out_path)

    print("✅ All 20 visual scenes successfully processed and standardized!")
    return processed_paths


if __name__ == "__main__":
    test_asset = {
        "scene_index": 0,
        "file_path": "test.jpg",
        "type": "image",
        "target_duration": 3.0
    }
    process_scene_asset(test_asset)