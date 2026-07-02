"""
Thumbnail generator — 8 distinct visual styles.
Style is picked by hashing the video title so it varies across videos
but is deterministic (same title = same style, useful for debugging).
"""

import os
import pickle
import hashlib
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy import VideoFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

THUMB_W, THUMB_H = 1280, 720
CHANNEL = "AMBIENT NEST HQ"
STYLES = [
    "bold_dark", "neon_cyber", "breaking_news", "cinematic_bars",
    "documentary", "vintage_retro", "minimal_clean", "mystery_hook",
]


# ── Utilities ─────────────────────────────────────────────────────────────────

def _pick_style(title):
    h = int(hashlib.md5(title.encode()).hexdigest(), 16)
    return STYLES[h % len(STYLES)]


def _load_font(size):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _extract_best_frame(video_path):
    clip = VideoFileClip(video_path)
    duration = clip.duration
    best, best_score = None, -1
    for pct in [0.12, 0.22, 0.38, 0.52, 0.68]:
        frame = clip.get_frame(duration * pct)
        score = float(np.std(frame))
        if score > best_score:
            best_score, best = score, frame
    clip.close()
    return Image.fromarray(best).resize((THUMB_W, THUMB_H), Image.LANCZOS)


def _draw_text_shadow(draw, pos, text, font, fill, shadow=(0, 0, 0, 210), offset=4):
    draw.text((pos[0]+offset, pos[1]+offset), text, font=font, fill=shadow)
    draw.text(pos, text, font=font, fill=fill)


def _wrap(text, max_chars=22):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]


# ── 8 Thumbnail Styles ────────────────────────────────────────────────────────

def _style_bold_dark(img, title):
    """Dark dramatic: red accent bar, massive white title, channel branding."""
    draw = ImageDraw.Draw(img.convert("RGBA"))
    # Dark overlay
    overlay = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(THUMB_H):
        a = int(180 * (y / THUMB_H) ** 1.2)
        od.line([(0, y), (THUMB_W, y)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (16, THUMB_H)], fill=(220, 30, 30))
    draw.text((28, 22), CHANNEL, font=_load_font(32), fill=(220, 30, 30))
    draw.line([(28, 66), (THUMB_W-30, 66)], fill=(160, 160, 160), width=2)
    lines = _wrap(title.upper(), 22)
    y = THUMB_H - len(lines) * 105 - 50
    for line in lines:
        _draw_text_shadow(draw, (28, y), line, _load_font(92), (255, 255, 255))
        y += 105
    return img


def _style_neon_cyber(img, title):
    """Cyberpunk: dark teal-shifted frame, neon cyan borders, glowing title."""
    arr = np.array(img).astype(np.float32) / 255
    arr[:,:,0] = np.clip(arr[:,:,0] * 0.6, 0, 1)
    arr[:,:,1] = np.clip(arr[:,:,1] * 0.85, 0, 1)
    arr[:,:,2] = np.clip(arr[:,:,2] * 1.4, 0, 1)
    arr = np.clip((arr - 0.5) * 1.4 + 0.5, 0, 1)
    img = Image.fromarray((arr * 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)
    # Neon border
    for i, color in enumerate([(0,255,220,180), (0,200,255,100)]):
        b = i * 6
        draw.rectangle([(b, b), (THUMB_W-b, THUMB_H-b)], outline=color, width=3)
    # Scan lines
    scan = Image.new("RGBA", (THUMB_W, THUMB_H), (0,0,0,0))
    sd = ImageDraw.Draw(scan)
    for y in range(0, THUMB_H, 4):
        sd.line([(0, y), (THUMB_W, y)], fill=(0, 0, 0, 40))
    img = Image.alpha_composite(img.convert("RGBA"), scan).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((28, 20), f"[ {CHANNEL} ]", font=_load_font(30), fill=(0, 255, 220))
    lines = _wrap(title.upper(), 20)
    y = THUMB_H - len(lines) * 110 - 40
    for line in lines:
        _draw_text_shadow(draw, (28, y), line, _load_font(98), (0, 255, 220), shadow=(0,0,0,220))
        y += 110
    # Glitch accent line
    draw.rectangle([(28, y+10), (400, y+14)], fill=(0, 255, 220))
    return img


def _style_breaking_news(img, title):
    """Breaking news: urgent red bottom ticker, bold white text."""
    img = img.copy()
    # Slight darken
    img = ImageEnhance.Brightness(img).enhance(0.75)
    draw = ImageDraw.Draw(img)
    # Red ticker bottom
    ticker_h = 130
    draw.rectangle([(0, THUMB_H-ticker_h), (THUMB_W, THUMB_H)], fill=(200, 20, 20))
    draw.rectangle([(0, THUMB_H-ticker_h), (THUMB_W, THUMB_H-ticker_h+4)], fill=(255, 200, 0))
    # BREAKING badge top-left
    draw.rectangle([(20, 20), (220, 68)], fill=(255, 200, 0))
    draw.text((28, 24), "● BREAKING", font=_load_font(32), fill=(0, 0, 0))
    draw.text((28, 74), CHANNEL, font=_load_font(26), fill=(255, 255, 255))
    # Title in ticker
    short = title[:55] + ("..." if len(title) > 55 else "")
    draw.text((20, THUMB_H-ticker_h+12), short, font=_load_font(52), fill=(255,255,255))
    return img


def _style_cinematic_bars(img, title):
    """Cinematic letterbox: black bars top/bottom, centered bold title."""
    img = ImageEnhance.Contrast(img).enhance(1.2)
    draw = ImageDraw.Draw(img)
    bar_h = 120
    draw.rectangle([(0, 0), (THUMB_W, bar_h)], fill=(0,0,0))
    draw.rectangle([(0, THUMB_H-bar_h), (THUMB_W, THUMB_H)], fill=(0,0,0))
    draw.text((THUMB_W//2 - 200, 30), CHANNEL, font=_load_font(28), fill=(180, 180, 180))
    lines = _wrap(title.upper(), 28)
    total_h = len(lines) * 66
    y = THUMB_H - bar_h - total_h - 20
    for line in lines:
        font = _load_font(60)
        bbox = draw.textbbox((0,0), line, font=font)
        x = (THUMB_W - (bbox[2]-bbox[0])) // 2
        _draw_text_shadow(draw, (x, y), line, font, (255,255,255))
        y += 66
    # Gold accent line
    draw.rectangle([(THUMB_W//4, THUMB_H-bar_h-6), (3*THUMB_W//4, THUMB_H-bar_h-2)], fill=(212,175,55))
    return img


def _style_documentary(img, title):
    """Documentary lower third: full image, dark vignette, title in lower third band."""
    # Vignette
    vignette = Image.new("RGBA", (THUMB_W, THUMB_H), (0,0,0,0))
    vd = ImageDraw.Draw(vignette)
    for i in range(200):
        a = int(180 * (i/200)**2)
        vd.rectangle([(i,i),(THUMB_W-i,THUMB_H-i)], outline=(0,0,0,a))
    img = Image.alpha_composite(img.convert("RGBA"), vignette)
    # Lower third dark band
    band = Image.new("RGBA", (THUMB_W, 160), (10, 10, 10, 210))
    img.paste(band, (0, THUMB_H-160), band)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    # Gold accent bar
    draw.rectangle([(0, THUMB_H-162), (THUMB_W, THUMB_H-158)], fill=(212,175,55))
    short = title[:65] + ("..." if len(title)>65 else "")
    draw.text((20, THUMB_H-148), short, font=_load_font(48), fill=(255,255,255))
    draw.text((20, THUMB_H-92), CHANNEL, font=_load_font(28), fill=(180,180,180))
    return img


def _style_vintage_retro(img, title):
    """Vintage sepia film look with aged border."""
    arr = np.array(img).astype(np.float32) / 255
    r = arr[:,:,0]*0.393 + arr[:,:,1]*0.769 + arr[:,:,2]*0.189
    g = arr[:,:,0]*0.349 + arr[:,:,1]*0.686 + arr[:,:,2]*0.168
    b = arr[:,:,0]*0.272 + arr[:,:,1]*0.534 + arr[:,:,2]*0.131
    arr = np.clip(np.stack([r*1.1, g, b*0.9], axis=2), 0, 1)
    img = Image.fromarray((arr*255).astype(np.uint8))
    # Vignette
    vig = Image.new("RGBA", (THUMB_W, THUMB_H), (0,0,0,0))
    for i in range(180):
        a = int(160*(i/180)**2)
        ImageDraw.Draw(vig).rectangle([(i,i),(THUMB_W-i,THUMB_H-i)], outline=(0,0,0,a))
    img = Image.alpha_composite(img.convert("RGBA"), vig).convert("RGB")
    draw = ImageDraw.Draw(img)
    # Aged border
    for w, c in [(8,(80,60,40)),(4,(120,90,60)),(2,(160,130,90))]:
        draw.rectangle([(w,w),(THUMB_W-w,THUMB_H-w)], outline=c, width=2)
    # Title
    lines = _wrap(title.upper(), 24)
    y = THUMB_H - len(lines)*90 - 60
    for line in lines:
        _draw_text_shadow(draw,(28,y),line,_load_font(80),(240,220,180),shadow=(40,25,10,200))
        y += 90
    draw.text((28, THUMB_H-44), CHANNEL, font=_load_font(28), fill=(200,175,130))
    return img


def _style_minimal_clean(img, title):
    """Clean modern: blurred bg, white panel, bold dark text."""
    bg = img.filter(ImageFilter.GaussianBlur(radius=20))
    bg = ImageEnhance.Brightness(bg).enhance(0.5)
    panel = Image.new("RGBA", (800, THUMB_H-80), (255,255,255,245))
    bg.paste(panel.convert("RGB"), (60, 40), panel.split()[3])
    draw = ImageDraw.Draw(bg)
    draw.rectangle([(60, 40), (860, 44)], fill=(220, 30, 30))
    draw.text((80, 55), CHANNEL, font=_load_font(30), fill=(220,30,30))
    lines = _wrap(title, 22)
    y = 110
    for line in lines:
        draw.text((80, y), line, font=_load_font(82), fill=(20,20,20))
        y += 94
    draw.rectangle([(60, THUMB_H-60), (860, THUMB_H-56)], fill=(20,20,20))
    return bg


def _style_mystery_hook(img, title):
    """Dark and mysterious: heavy vignette, spotlight, intrigue framing."""
    # Very dark overlay
    arr = np.array(img).astype(np.float32)/255
    arr = np.clip(arr * 0.35, 0, 1)
    # Spotlight center
    cx, cy = THUMB_W//2, THUMB_H//2
    Y, X = np.ogrid[:THUMB_H, :THUMB_W]
    dist = np.sqrt((X-cx)**2 + (Y-cy)**2)
    spot = np.clip(1 - dist/600, 0, 1)[:,:,np.newaxis]
    arr = np.clip(arr + spot * 0.5, 0, 1)
    img = Image.fromarray((arr*255).astype(np.uint8))
    draw = ImageDraw.Draw(img)
    # Question mark large (mystery feel)
    draw.text((THUMB_W-160, 20), "?", font=_load_font(180), fill=(220,30,30,180))
    draw.text((28, 24), CHANNEL, font=_load_font(28), fill=(180,180,180))
    lines = _wrap(title.upper(), 22)
    y = THUMB_H - len(lines)*100 - 50
    for line in lines:
        _draw_text_shadow(draw, (28,y), line, _load_font(88), (255,255,255))
        y += 100
    # Red accent bottom
    draw.rectangle([(0, THUMB_H-8), (THUMB_W, THUMB_H)], fill=(220,30,30))
    return img


STYLE_FUNCS = {
    "bold_dark":     _style_bold_dark,
    "neon_cyber":    _style_neon_cyber,
    "breaking_news": _style_breaking_news,
    "cinematic_bars":_style_cinematic_bars,
    "documentary":   _style_documentary,
    "vintage_retro": _style_vintage_retro,
    "minimal_clean": _style_minimal_clean,
    "mystery_hook":  _style_mystery_hook,
}


def generate_thumbnail(video_path, title, output_path="thumbnail.jpg"):
    print(f"🖼️  Generating thumbnail (style: {_pick_style(title)})...")
    try:
        frame = _extract_best_frame(video_path)
        style_name = _pick_style(title)
        styled = STYLE_FUNCS[style_name](frame, title)
        styled.save(output_path, "JPEG", quality=95)
        print(f"✅ Thumbnail saved [{style_name}]: {output_path}")
        return output_path
    except Exception as e:
        print(f"⚠️ Thumbnail generation failed: {e}")
        return None


def upload_thumbnail(video_id, thumbnail_path):
    if not thumbnail_path or not os.path.exists("token.pickle"):
        print("⚠️  Skipping thumbnail upload.")
        return
    print(f"🚀 Uploading thumbnail to YouTube video {video_id}...")
    with open("token.pickle", "rb") as token:
        creds = pickle.load(token)
    youtube = build("youtube", "v3", credentials=creds)
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
        ).execute()
        print("✅ Thumbnail live on YouTube!")
    except Exception as e:
        print(f"⚠️  Thumbnail upload failed: {e}")
        print("   Note: Account must be phone-verified for custom thumbnails.")
    finally:
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except OSError:
                pass