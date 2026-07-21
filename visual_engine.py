"""
Financial Visual Engine
Processes downloaded 3-second stock video clips and static images.
Standardizes resolution to 1080x1920 (9:16 portrait) and applies smooth 
Ken Burns zoom effects to static photos for high visual retention.
"""

import os
import shutil as _shutil
from PIL import Image, ImageDraw, ImageFont

# MoviePy compatibility handler
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
    Uses MoviePy v2 compatible helper methods.
    """
    img_clip = ImageClip(image_path)
    
    # Duration setting (v2 vs v1)
    if hasattr(img_clip, "with_duration"):
        img_clip = img_clip.with_duration(duration)
    else:
        img_clip = img_clip.set_duration(duration)

    # Resizing to 1920 height
    if hasattr(img_clip, "resized"):
        img_clip = img_clip.resized(height=target_size[1])
        if img_clip.w < target_size[0]:
            img_clip = img_clip.resized(width=target_size[0])
        
        # Center crop
        img_clip = img_clip.cropped(x_center=img_clip.w / 2, y_center=img_clip.h / 2, width=1080, height=1920)
        
        # Zoom function
        zoomed_clip = img_clip.resized(lambda t: 1.0 + 0.05 * t)
        pos_clip = zoomed_clip.with_position("center") if hasattr(zoomed_clip, "with_position") else zoomed_clip.set_position("center")
        final_clip = CompositeVideoClip([pos_clip], size=target_size)
        return final_clip.with_duration(duration) if hasattr(final_clip, "with_duration") else final_clip.set_duration(duration)
    
    else:
        # Legacy MoviePy v1 fallback
        img_clip = img_clip.resize(height=target_size[1])
        if img_clip.w < target_size[0]:
            img_clip = img_clip.resize(width=target_size[0])

        img_clip = img_clip.crop(x_center=img_clip.w / 2, y_center=img_clip.h / 2, width=1080, height=1920)
        zoomed_clip = img_clip.resize(lambda t: 1.0 + 0.05 * t)
        final_clip = CompositeVideoClip([zoomed_clip.set_position("center")], size=target_size)
        return final_clip.set_duration(duration)


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
            clip = VideoFileClip(raw_path)

            # MoviePy v2 subclip vs subclipped
            if hasattr(clip, "subclipped"):
                clip = clip.subclipped(0, target_duration) if clip.duration >= target_duration else clip
            elif hasattr(clip, "subclip"):
                clip = clip.subclip(0, target_duration) if clip.duration >= target_duration else clip

            # MoviePy v2 resize vs resized
            if hasattr(clip, "resized"):
                clip = clip.resized(height=1920)
                if clip.w > 1080:
                    clip = clip.cropped(x_center=clip.w / 2, width=1080)
                elif clip.w < 1080:
                    clip = clip.resized(width=1080)
            else:
                clip = clip.resize(height=1920)
                if clip.w > 1080:
                    clip = clip.crop(x_center=clip.w / 2, width=1080)
                elif clip.w < 1080:
                    clip = clip.resize(width=1080)

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