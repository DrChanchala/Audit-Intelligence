import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from test_render_frame import create_base_canvas, draw_header_bar, draw_footer_caption, W, H, get_font, FONT_PATH_BOLD, FONT_PATH_REG

def draw_outro_card(canvas):
    draw = ImageDraw.Draw(canvas)
    
    # Center Card
    card_x = 180
    card_y = 100
    card_w = 920
    card_h = 470
    
    # Soft shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([(card_x - 6, card_y + 6), (card_x + card_w + 6, card_y + card_h + 12)], radius=24, fill=(0, 0, 0, 40))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas.alpha_composite(shadow)
    
    # White card container
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=20, fill=(255, 255, 255, 255), outline=(203, 213, 225, 255), width=2)
    
    # Top brand bar
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 12)], radius=20, fill=(29, 78, 216, 255))
    draw.rectangle([(card_x, card_y + 6), (card_x + card_w, card_y + 12)], fill=(29, 78, 216, 255))
    
    # Brand title
    draw.text((card_x + 60, card_y + 40), "SiteIQ", fill=(15, 23, 42, 255), font=get_font(FONT_PATH_BOLD, 46))
    
    # Tagline
    draw.text((card_x + 60, card_y + 100), "SITEIQ PLATFORM", fill=(13, 148, 136, 255), font=get_font(FONT_PATH_BOLD, 15))
    draw.text((card_x + 60, card_y + 125), "Construction progress you can trust.", fill=(30, 41, 59, 255), font=get_font(FONT_PATH_BOLD, 22))
    draw.text((card_x + 60, card_y + 160), "Automated camera vision • Field mobile capture • L4 Schedule Baseline • 4-Stream S-Curve", fill=(100, 116, 139, 255), font=get_font(FONT_PATH_REG, 15))

    # 4 Pillar mini-cards
    pillars = [
        ("Autonomous Cameras", "Continuous Mode A tracking", (37, 99, 235)),
        ("Mobile Field Photos", "Verified with Gemini Vision", (13, 148, 136)),
        ("4-Stream Dashboard", "Traceable certified progress", (124, 58, 237)),
        ("Instant AI Chatbot", "Ask any question 24/7", (217, 119, 6))
    ]
    
    px = card_x + 50
    pw = 190
    for idx, (p_title, p_sub, p_col) in enumerate(pillars):
        bx = px + idx * (pw + 20)
        by = card_y + 205
        draw.rounded_rectangle([(bx, by), (bx + pw, by + 105)], radius=12, fill=(248, 250, 252, 255), outline=(226, 232, 240, 255), width=1)
        draw.rounded_rectangle([(bx + 12, by + 12), (bx + 20, by + 28)], radius=4, fill=p_col)
        draw.text((bx + 28, by + 13), p_title.split()[0], fill=(15, 23, 42, 255), font=get_font(FONT_PATH_BOLD, 14))
        draw.text((bx + 12, by + 34), p_title, fill=(15, 23, 42, 255), font=get_font(FONT_PATH_BOLD, 13))
        draw.text((bx + 12, by + 58), p_sub, fill=(100, 116, 139, 255), font=get_font(FONT_PATH_REG, 11))

    # Big banner at bottom of card
    bx1 = card_x + 50
    bx2 = card_x + card_w - 50
    by1 = card_y + 340
    by2 = card_y + 420
    draw.rounded_rectangle([(bx1, by1), (bx2, by2)], radius=14, fill=(239, 246, 255, 255), outline=(29, 78, 216, 255), width=2)
    draw.text((bx1 + 30, by1 + 18), "AI brings the efficiency you need.", fill=(29, 78, 216, 255), font=get_font(FONT_PATH_BOLD, 26))
    draw.text((bx1 + 30, by1 + 50), "Empowering owners, contractors, and project managers with verified ground truth.", fill=(71, 85, 105, 255), font=get_font(FONT_PATH_REG, 14))

canvas = create_base_canvas()
draw_outro_card(canvas)
draw = ImageDraw.Draw(canvas)
draw_header_bar(draw, "SITEIQ • THE FUTURE OF CONSTRUCTION", "AI-Powered Verification")
draw_footer_caption(draw, "AI brings the efficiency you need.", "SiteIQ • Precision Construction Intelligence", 1.0)
canvas.convert("RGB").save("frame_scene6.png")
print("Saved frame_scene6.png")
