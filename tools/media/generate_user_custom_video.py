import os
import subprocess
import wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio
import imageio_ffmpeg

W, H = 1280, 720
FPS = 24
TOTAL_DURATION = 20.0
TOTAL_FRAMES = int(FPS * TOTAL_DURATION)  # 480 frames

FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_REG = "C:/Windows/Fonts/segoeui.ttf"

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

font_header_title = get_font(FONT_BOLD, 22)
font_header_sub = get_font(FONT_REG, 15)
font_badge = get_font(FONT_BOLD, 13)
font_caption = get_font(FONT_BOLD, 24)
font_caption_sub = get_font(FONT_REG, 17)

img_paths = {
    "landing": r"C:/Users/Chanchala/.gemini/antigravity/brain/b9c6cadc-aedc-48cc-9328-73b56488cb56/.user_uploaded/media_1792089502021.png",
    "cameras_field": r"C:/Users/Chanchala/.gemini/antigravity/brain/b9c6cadc-aedc-48cc-9328-73b56488cb56/.user_uploaded/media_1792089567346.png",
    "schedule": r"C:/Users/Chanchala/.gemini/antigravity/brain/b9c6cadc-aedc-48cc-9328-73b56488cb56/.user_uploaded/media_1792089556802.png",
    "dashboard": r"C:/Users/Chanchala/.gemini/antigravity/brain/b9c6cadc-aedc-48cc-9328-73b56488cb56/.user_uploaded/media_1792089530172.png",
    "ai_chat": r"C:/Users/Chanchala/.gemini/antigravity/brain/b9c6cadc-aedc-48cc-9328-73b56488cb56/.user_uploaded/media_1792089549130.png"
}

# Pre-load images
loaded_images = {k: Image.open(v).convert("RGBA") for k, v in img_paths.items()}

# Cache base canvas
def get_base_canvas():
    base = Image.new("RGBA", (W, H), (248, 250, 252, 255))
    draw = ImageDraw.Draw(base)
    for y in range(H):
        ratio = y / float(H)
        r = int(248 + (235 - 248) * ratio)
        g = int(250 + (242 - 250) * ratio)
        b = int(252 + (255 - 252) * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))
    grid_color = (226, 232, 240, 160)
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill=grid_color, width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill=grid_color, width=1)
    return base

BASE_CANVAS = get_base_canvas()

def draw_header(draw, badge_text, right_info="SiteIQ Platform"):
    draw.rectangle([(0, 0), (W, 64)], fill=(255, 255, 255, 245))
    draw.line([(0, 64), (W, 64)], fill=(203, 213, 225, 255), width=1)

    draw.text((40, 18), "SiteIQ", fill=(15, 23, 42, 255), font=font_header_title)
    draw.text((115, 22), "AI Construction Intelligence", fill=(100, 116, 139, 255), font=font_header_sub)

    badge_w = draw.textlength(badge_text, font=font_badge) + 26
    bx1 = (W - badge_w) / 2
    bx2 = bx1 + badge_w
    draw.rounded_rectangle([(bx1, 16), (bx2, 48)], radius=16, fill=(239, 246, 255, 255), outline=(59, 130, 246, 255), width=1)
    draw.text((bx1 + 13, 24), badge_text, fill=(29, 78, 216, 255), font=font_badge)

    rw = draw.textlength(right_info, font=font_badge)
    draw.text((W - rw - 40, 24), right_info, fill=(71, 85, 105, 255), font=font_badge)

def draw_footer_caption(draw, caption_title, caption_sub="", progress=0.0):
    card_w = 1000
    card_h = 76
    cx1 = (W - card_w) / 2
    cy1 = H - card_h - 26
    cx2 = cx1 + card_w
    cy2 = cy1 + card_h

    draw.rounded_rectangle([(cx1, cy1), (cx2, cy2)], radius=14, fill=(255, 255, 255, 252), outline=(29, 78, 216, 255), width=2)
    draw.rounded_rectangle([(cx1 + 12, cy1 + 14), (cx1 + 18, cy2 - 14)], radius=3, fill=(29, 78, 216, 255))
    draw.text((cx1 + 32, cy1 + 13), caption_title, fill=(15, 23, 42, 255), font=font_caption)
    if caption_sub:
        draw.text((cx1 + 32, cy1 + 43), caption_sub, fill=(100, 116, 139, 255), font=font_caption_sub)

    # Animated progress bar
    draw.rectangle([(0, H - 5), (W, H)], fill=(226, 232, 240, 255))
    draw.rectangle([(0, H - 5), (int(W * max(0.0, min(1.0, progress))), H)], fill=(29, 78, 216, 255))

def render_image_scene(img_key, badge_text, cap_title, cap_sub, progress, local_t):
    canvas = BASE_CANVAS.copy()
    img = loaded_images[img_key]

    card_x = 90
    card_y = 86
    card_w = 1100
    card_h = 510

    # Gentle subtle zoom (1.00 -> 1.03) over local_t (0.0 to 1.0)
    zoom = 1.00 + 0.03 * local_t

    # Card shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([(card_x - 4, card_y + 4), (card_x + card_w + 4, card_y + card_h + 10)], radius=16, fill=(0, 0, 0, 42))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    canvas.alpha_composite(shadow)

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=14, fill=(255, 255, 255, 255), outline=(203, 213, 225, 255), width=1)

    # Window titlebar
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 36)], radius=14, fill=(241, 245, 249, 255))
    draw.rectangle([(card_x, card_y + 20), (card_x + card_w, card_y + 36)], fill=(241, 245, 249, 255))
    draw.line([(card_x, card_y + 36), (card_x + card_w, card_y + 36)], fill=(226, 232, 240, 255), width=1)

    draw.ellipse([(card_x + 14, card_y + 12), (card_x + 24, card_y + 22)], fill=(239, 68, 68, 255))
    draw.ellipse([(card_x + 32, card_y + 12), (card_x + 42, card_y + 22)], fill=(245, 158, 11, 255))
    draw.ellipse([(card_x + 50, card_y + 12), (card_x + 60, card_y + 22)], fill=(16, 185, 129, 255))
    draw.text((card_x + card_w/2 - 70, card_y + 9), "SiteIQ Intelligence Engine", fill=(100, 116, 139, 255), font=get_font(FONT_BOLD, 12))

    vp_x = card_x + 1
    vp_y = card_y + 37
    vp_w = card_w - 2
    vp_h = card_h - 38

    scale = min(vp_w / img.width, vp_h / img.height) * zoom
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    paste_x = vp_x + (vp_w - new_w) // 2
    paste_y = vp_y + (vp_h - new_h) // 2

    viewport = Image.new("RGBA", (vp_w, vp_h), (255, 255, 255, 255))
    viewport.paste(resized_img, (paste_x - vp_x, paste_y - vp_y), resized_img if resized_img.mode == 'RGBA' else None)
    canvas.paste(viewport, (vp_x, vp_y))

    # Overlays
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, badge_text)
    draw_footer_caption(draw, cap_title, cap_sub, progress)
    return canvas

def render_outro_scene(progress, local_t):
    canvas = BASE_CANVAS.copy()
    draw = ImageDraw.Draw(canvas)

    card_x = 180
    card_y = 100
    card_w = 920
    card_h = 470

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([(card_x - 6, card_y + 6), (card_x + card_w + 6, card_y + card_h + 12)], radius=24, fill=(0, 0, 0, 42))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas.alpha_composite(shadow)

    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=20, fill=(255, 255, 255, 255), outline=(203, 213, 225, 255), width=2)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 12)], radius=20, fill=(29, 78, 216, 255))
    draw.rectangle([(card_x, card_y + 6), (card_x + card_w, card_y + 12)], fill=(29, 78, 216, 255))

    draw.text((card_x + 60, card_y + 36), "SiteIQ", fill=(15, 23, 42, 255), font=get_font(FONT_BOLD, 46))
    draw.text((card_x + 60, card_y + 96), "SITEIQ PLATFORM", fill=(13, 148, 136, 255), font=get_font(FONT_BOLD, 15))
    draw.text((card_x + 60, card_y + 122), "Construction progress you can trust.", fill=(30, 41, 59, 255), font=get_font(FONT_BOLD, 22))
    draw.text((card_x + 60, card_y + 158), "Automated camera vision • Field mobile capture • L4 Schedule Baseline • 4-Stream S-Curve", fill=(100, 116, 139, 255), font=get_font(FONT_REG, 15))

    pillars = [
        ("Autonomous Cameras", "Mode A 24/7 Vision", (37, 99, 235)),
        ("Mobile Field Photos", "Mode B Gemini Vision", (13, 148, 136)),
        ("4-Stream Dashboard", "Certified S-Curve", (124, 58, 237)),
        ("Project AI Chatbot", "Instant Answers 24/7", (217, 119, 6))
    ]

    px = card_x + 50
    pw = 190
    for idx, (p_title, p_sub, p_col) in enumerate(pillars):
        bx = px + idx * (pw + 20)
        by = card_y + 200
        draw.rounded_rectangle([(bx, by), (bx + pw, by + 105)], radius=12, fill=(248, 250, 252, 255), outline=(226, 232, 240, 255), width=1)
        draw.rounded_rectangle([(bx + 14, by + 14), (bx + 20, by + 30)], radius=3, fill=p_col)
        draw.text((bx + 14, by + 36), p_title, fill=(15, 23, 42, 255), font=get_font(FONT_BOLD, 14))
        draw.text((bx + 14, by + 62), p_sub, fill=(100, 116, 139, 255), font=get_font(FONT_REG, 12))

    bx1 = card_x + 50
    bx2 = card_x + card_w - 50
    by1 = card_y + 335
    by2 = card_y + 425
    draw.rounded_rectangle([(bx1, by1), (bx2, by2)], radius=14, fill=(239, 246, 255, 255), outline=(29, 78, 216, 255), width=2)
    draw.text((bx1 + 30, by1 + 18), "AI brings the efficiency you need.", fill=(29, 78, 216, 255), font=get_font(FONT_BOLD, 26))
    draw.text((bx1 + 30, by1 + 54), "Empowering owners, contractors, and project managers with verified ground truth.", fill=(71, 85, 105, 255), font=get_font(FONT_REG, 14))

    draw = ImageDraw.Draw(canvas)
    draw_header(draw, "SITEIQ • THE FUTURE OF CONSTRUCTION", "AI-Powered Verification")
    draw_footer_caption(draw, "AI brings the efficiency you need.", "SiteIQ • Precision Construction Intelligence", progress)
    return canvas

# Scene definitions
scenes = [
    {
        "name": "Scene 1: Landing / Trust",
        "start_frame": 0,
        "end_frame": 91,
        "render": lambda p, lt: render_image_scene(
            "landing",
            "SITEIQ PLATFORM",
            "Construction progress you can trust.",
            "SiteIQ • AI-Powered Construction Intelligence",
            p, lt
        )
    },
    {
        "name": "Scene 2: Cameras & Field",
        "start_frame": 91,
        "end_frame": 158,
        "render": lambda p, lt: render_image_scene(
            "cameras_field",
            "DUAL-MODE VERIFICATION STREAM",
            "SiteIQ checks site cameras and field photos...",
            "Fixed Autonomous Cameras (Mode A) & Mobile Field Evidence (Mode B)",
            p, lt
        )
    },
    {
        "name": "Scene 3: Schedule Baseline",
        "start_frame": 158,
        "end_frame": 225,
        "render": lambda p, lt: render_image_scene(
            "schedule",
            "L4 MASTER BASELINE ENGINE",
            "...against your schedule.",
            "311 Canonical WBS Activities • 100% Weight Validated",
            p, lt
        )
    },
    {
        "name": "Scene 4: Dashboard",
        "start_frame": 225,
        "end_frame": 302,
        "render": lambda p, lt: render_image_scene(
            "dashboard",
            "INTEGRATED 4-STREAM TRUTH DASHBOARD",
            "Track progress on the dashboard,",
            "Planned vs AI Automated vs Field Observed vs PM Approved",
            p, lt
        )
    },
    {
        "name": "Scene 5: AI Assistant Chat",
        "start_frame": 302,
        "end_frame": 396,
        "render": lambda p, lt: render_image_scene(
            "ai_chat",
            "PROJECT AI ASSISTANT",
            "...and chat with it to get any detail instantly.",
            "NLP Schedule Intelligence, Risk Triage & Daily Briefings",
            p, lt
        )
    },
    {
        "name": "Scene 6: Outro / Efficiency",
        "start_frame": 396,
        "end_frame": 480,
        "render": lambda p, lt: render_outro_scene(p, lt)
    }
]

def render_video():
    temp_silent_mp4 = "static/temp_siteiq_silent.mp4"
    final_output_mp4 = "static/SiteIQ_Custom_Showcase.mp4"
    audio_wav = "narration_synced.wav"

    print(f"Rendering {TOTAL_FRAMES} frames ({TOTAL_DURATION}s @ {FPS} FPS)...")
    writer = imageio.get_writer(
        temp_silent_mp4,
        fps=FPS,
        codec='libx264',
        pixelformat='yuv420p',
        bitrate='3000k',
        output_params=['-crf', '18', '-preset', 'medium']
    )

    fade_len = 6  # 6 frames transition

    for f_idx in range(TOTAL_FRAMES):
        global_progress = f_idx / float(TOTAL_FRAMES)
        
        # Determine current scene
        cur_scene_idx = 0
        for idx, sc in enumerate(scenes):
            if sc["start_frame"] <= f_idx < sc["end_frame"]:
                cur_scene_idx = idx
                break
        
        sc = scenes[cur_scene_idx]
        sc_len = sc["end_frame"] - sc["start_frame"]
        local_t = (f_idx - sc["start_frame"]) / float(sc_len)
        
        frame_img = sc["render"](global_progress, local_t)

        # Cross-dissolve transition if near boundary and previous scene exists
        frame_offset = f_idx - sc["start_frame"]
        if frame_offset < fade_len and cur_scene_idx > 0:
            prev_sc = scenes[cur_scene_idx - 1]
            prev_len = prev_sc["end_frame"] - prev_sc["start_frame"]
            prev_img = prev_sc["render"](global_progress, 1.0)
            
            alpha = frame_offset / float(fade_len)
            blended = Image.blend(prev_img, frame_img, alpha)
            np_frame = np.array(blended.convert("RGB"))
        else:
            np_frame = np.array(frame_img.convert("RGB"))

        writer.append_data(np_frame)

        if f_idx % 48 == 0:
            print(f"  Rendered frame {f_idx}/{TOTAL_FRAMES} ({f_idx/FPS:.1f}s)...")

    writer.close()
    print("Silent video generated successfully.")

    # Multiplex with ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"Multiplexing audio using {ffmpeg_exe}...")
    
    cmd = [
        ffmpeg_exe, "-y",
        "-i", temp_silent_mp4,
        "-i", audio_wav,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_output_mp4
    ]
    subprocess.run(cmd, check=True)

    if os.path.exists(temp_silent_mp4):
        os.remove(temp_silent_mp4)

    # Also update PyCray_SiteIQ_30s_Product_Video.mp4 so the existing in-app modal plays this custom showcase!
    import shutil
    shutil.copyfile(final_output_mp4, "static/PyCray_SiteIQ_30s_Product_Video.mp4")

    print(f"SUCCESS! Created {final_output_mp4} ({os.path.getsize(final_output_mp4)} bytes).")

if __name__ == "__main__":
    render_video()
