import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1280, 720

FONT_PATH_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_PATH_REG = "C:/Windows/Fonts/segoeui.ttf"

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

font_title = get_font(FONT_PATH_BOLD, 28)
font_subtitle = get_font(FONT_PATH_REG, 20)
font_badge = get_font(FONT_PATH_BOLD, 13)
font_caption = get_font(FONT_PATH_BOLD, 24)
font_caption_sub = get_font(FONT_PATH_REG, 17)

img_paths = {
    "landing": r"C:/Users/Chanchala/.gemini/antigravity/brain/b9c6cadc-aedc-48cc-9328-73b56488cb56/.user_uploaded/media_1792089502021.png",
    "dashboard": r"C:/Users/Chanchala/.gemini/antigravity/brain/b9c6cadc-aedc-48cc-9328-73b56488cb56/.user_uploaded/media_1792089530172.png",
    "ai_chat": r"C:/Users/Chanchala/.gemini/antigravity/brain/b9c6cadc-aedc-48cc-9328-73b56488cb56/.user_uploaded/media_1792089549130.png",
    "schedule": r"C:/Users/Chanchala/.gemini/antigravity/brain/b9c6cadc-aedc-48cc-9328-73b56488cb56/.user_uploaded/media_1792089556802.png",
    "cameras_field": r"C:/Users/Chanchala/.gemini/antigravity/brain/b9c6cadc-aedc-48cc-9328-73b56488cb56/.user_uploaded/media_1792089567346.png"
}

def create_base_canvas():
    # Subtle gradient background from slate-50 to blue-50
    base = Image.new("RGBA", (W, H), (248, 250, 252, 255))
    draw = ImageDraw.Draw(base)
    for y in range(H):
        ratio = y / float(H)
        r = int(248 + (235 - 248) * ratio)
        g = int(250 + (242 - 250) * ratio)
        b = int(252 + (255 - 252) * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))
    
    # Subtle grid lines
    grid_color = (226, 232, 240, 160)
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill=grid_color, width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill=grid_color, width=1)
    return base

def draw_header_bar(draw, badge_text, right_info="SiteIQ Platform"):
    # Header container
    draw.rectangle([(0, 0), (W, 64)], fill=(255, 255, 255, 245))
    draw.line([(0, 64), (W, 64)], fill=(203, 213, 225, 255), width=1)

    # Logo / Brand
    draw.text((40, 18), "SiteIQ", fill=(15, 23, 42, 255), font=get_font(FONT_PATH_BOLD, 22))
    draw.text((115, 21), "AI Construction Progress", fill=(100, 116, 139, 255), font=get_font(FONT_PATH_REG, 15))

    # Center Badge
    badge_w = draw.textlength(badge_text, font=font_badge) + 24
    bx1 = (W - badge_w) / 2
    bx2 = bx1 + badge_w
    draw.rounded_rectangle([(bx1, 16), (bx2, 48)], radius=16, fill=(239, 246, 255, 255), outline=(59, 130, 246, 255), width=1)
    draw.text((bx1 + 12, 24), badge_text, fill=(29, 78, 216, 255), font=font_badge)

    # Right info
    rw = draw.textlength(right_info, font=font_badge)
    draw.text((W - rw - 40, 24), right_info, fill=(71, 85, 105, 255), font=font_badge)

def draw_footer_caption(draw, caption_title, caption_sub="", progress=0.5):
    # Caption card
    card_w = 980
    card_h = 76
    cx1 = (W - card_w) / 2
    cy1 = H - card_h - 28
    cx2 = cx1 + card_w
    cy2 = cy1 + card_h

    # Card background with blue accent border
    draw.rounded_rectangle([(cx1, cy1), (cx2, cy2)], radius=14, fill=(255, 255, 255, 250), outline=(29, 78, 216, 255), width=2)
    
    # Left accent indicator
    draw.rounded_rectangle([(cx1 + 12, cy1 + 14), (cx1 + 18, cy2 - 14)], radius=3, fill=(29, 78, 216, 255))

    # Caption text
    draw.text((cx1 + 32, cy1 + 14), caption_title, fill=(15, 23, 42, 255), font=font_caption)
    if caption_sub:
        draw.text((cx1 + 32, cy1 + 44), caption_sub, fill=(100, 116, 139, 255), font=font_caption_sub)

    # Progress bar at bottom
    draw.rectangle([(0, H - 5), (W, H)], fill=(226, 232, 240, 255))
    draw.rectangle([(0, H - 5), (int(W * progress), H)], fill=(29, 78, 216, 255))

def draw_app_frame(canvas, img_path, zoom=1.0, pan_x=0, pan_y=0):
    img = Image.open(img_path).convert("RGBA")
    
    # Card dimensions
    card_x = 90
    card_y = 86
    card_w = 1100
    card_h = 510

    # Draw card shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([(card_x - 4, card_y + 4), (card_x + card_w + 4, card_y + card_h + 10)], radius=16, fill=(0, 0, 0, 45))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    canvas.alpha_composite(shadow)

    # Draw card window frame
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=14, fill=(255, 255, 255, 255), outline=(203, 213, 225, 255), width=1)

    # Window titlebar
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 36)], radius=14, fill=(241, 245, 249, 255))
    draw.rectangle([(card_x, card_y + 20), (card_x + card_w, card_y + 36)], fill=(241, 245, 249, 255))
    draw.line([(card_x, card_y + 36), (card_x + card_w, card_y + 36)], fill=(226, 232, 240, 255), width=1)
    
    # Window buttons
    draw.ellipse([(card_x + 14, card_y + 12), (card_x + 24, card_y + 22)], fill=(239, 68, 68, 255))
    draw.ellipse([(card_x + 32, card_y + 12), (card_x + 42, card_y + 22)], fill=(245, 158, 11, 255))
    draw.ellipse([(card_x + 50, card_y + 12), (card_x + 60, card_y + 22)], fill=(16, 185, 129, 255))
    draw.text((card_x + card_w/2 - 70, card_y + 9), "SiteIQ Intelligence Engine", fill=(100, 116, 139, 255), font=get_font(FONT_PATH_BOLD, 12))

    # Inner image viewport
    vp_x = card_x + 1
    vp_y = card_y + 37
    vp_w = card_w - 2
    vp_h = card_h - 38

    # Apply zoom and pan to source image
    # Maintain aspect ratio with fit
    scale = min(vp_w / img.width, vp_h / img.height) * zoom
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Center + pan
    paste_x = vp_x + (vp_w - new_w) // 2 + int(pan_x)
    paste_y = vp_y + (vp_h - new_h) // 2 + int(pan_y)

    # Crop to viewport
    viewport = Image.new("RGBA", (vp_w, vp_h), (255, 255, 255, 255))
    viewport.paste(resized_img, (paste_x - vp_x, paste_y - vp_y), resized_img if resized_img.mode == 'RGBA' else None)
    
    canvas.paste(viewport, (vp_x, vp_y))

# Render one frame for each scene
test_scenes = [
    ("frame_scene1.png", "landing", "DUAL-TRACK QUALITY ASSURANCE", "Construction progress you can trust.", "SiteIQ • SiteIQ Platform", 0.15),
    ("frame_scene2.png", "cameras_field", "DUAL-MODE VERIFICATION STREAM", "SiteIQ checks site cameras and field photos...", "Fixed Autonomous Cameras (Mode A) & Mobile Field Evidence (Mode B)", 0.35),
    ("frame_scene3.png", "schedule", "L4 MASTER BASELINE ENGINE", "...against your schedule.", "311 Canonical WBS Activities • 100% Weight Validated", 0.50),
    ("frame_scene4.png", "dashboard", "INTEGRATED 4-STREAM TRUTH", "Track progress on the dashboard,", "Planned vs AI Automated vs Field Observed vs PM Approved", 0.70),
    ("frame_scene5.png", "ai_chat", "SCHEDULE NLP INTELLIGENCE", "...and chat with it to get any detail instantly.", "Instant WBS Queries, Discrepancy Audits & Risk Triage", 0.85),
]

for fname, key, badge, cap_title, cap_sub, prog in test_scenes:
    canvas = create_base_canvas()
    draw_app_frame(canvas, img_paths[key], zoom=1.02)
    draw = ImageDraw.Draw(canvas)
    draw_header_bar(draw, badge)
    draw_footer_caption(draw, cap_title, cap_sub, prog)
    canvas.convert("RGB").save(fname)
    print(f"Saved {fname}")
