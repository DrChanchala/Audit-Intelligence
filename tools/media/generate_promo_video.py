"""
PyCray_SiteIQ — 30-Second Video Generator
Renders a professional 1280x720 HD 24fps video (720 frames, 30.0 seconds)
narrating the product features with animated typography, cards, and data visualizations.
Synchronizes with narration.wav using bundled ffmpeg.
"""
import os
import math
import subprocess
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import imageio
import imageio_ffmpeg

WIDTH = 1280
HEIGHT = 720
FPS = 24
TOTAL_SECONDS = 30
TOTAL_FRAMES = FPS * TOTAL_SECONDS  # 720 frames

# Fonts
FONT_BOLD_PATH = r"C:\Windows\Fonts\segoeuib.ttf"
FONT_REG_PATH = r"C:\Windows\Fonts\segoeui.ttf"

def get_font(size, bold=False):
    path = FONT_BOLD_PATH if bold else FONT_REG_PATH
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

font_title = get_font(34, bold=True)
font_subtitle = get_font(20, bold=True)
font_heading = get_font(26, bold=True)
font_subheading = get_font(18, bold=False)
font_body = get_font(15, bold=False)
font_body_bold = get_font(15, bold=True)
font_small = get_font(12, bold=False)
font_small_bold = get_font(12, bold=True)
font_kpi_num = get_font(32, bold=True)

# Color Palette (Strict White, Blue, Black)
COLOR_BG = (255, 255, 255)
COLOR_SURFACE = (248, 250, 255)
COLOR_BORDER = (191, 219, 254)
COLOR_BORDER_STRONG = (59, 130, 246)
COLOR_PRIMARY = (29, 78, 216)
COLOR_PRIMARY_DARK = (30, 58, 138)
COLOR_TEXT_BLACK = (17, 24, 39)
COLOR_TEXT_MUTED = (75, 85, 99)
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_ACCENT_BG = (219, 234, 254)
COLOR_GREEN = (22, 101, 52)
COLOR_GREEN_BG = (220, 252, 231)

def draw_top_nav(draw, current_sec):
    # Header background
    draw.rectangle([0, 0, WIDTH, 65], fill=(255, 255, 255), outline=COLOR_BORDER, width=1)
    
    # Icon square
    draw.rounded_rectangle([25, 12, 65, 52], radius=8, fill=COLOR_PRIMARY)
    draw.text((36, 17), "IQ", font=font_subheading, fill=COLOR_TEXT_WHITE)
    
    # App Name
    draw.text((75, 12), "PyCray_SiteIQ", font=font_subtitle, fill=COLOR_TEXT_BLACK)
    draw.text((75, 36), "Dual-Mode AI Construction Progress Platform", font=font_small, fill=COLOR_TEXT_MUTED)
    
    # Badge
    draw.rounded_rectangle([390, 20, 500, 44], radius=6, fill=COLOR_ACCENT_BG, outline=COLOR_BORDER, width=1)
    draw.text((400, 24), "DUAL-MODE AI", font=font_small_bold, fill=COLOR_PRIMARY_DARK)
    
    # Live time indicator
    time_str = f"00:{int(current_sec):02d} / 00:30"
    draw.text((WIDTH - 180, 22), time_str, font=font_subtitle, fill=COLOR_PRIMARY)

def draw_bottom_bar(draw, frame_idx, scene_name):
    # Bottom Bar
    draw.rectangle([0, HEIGHT - 45, WIDTH, HEIGHT], fill=(248, 250, 255), outline=COLOR_BORDER, width=1)
    
    # Scene Label
    draw.text((30, HEIGHT - 32), scene_name.upper(), font=font_small_bold, fill=COLOR_PRIMARY_DARK)
    draw.text((WIDTH - 300, HEIGHT - 32), "Grand Horizon Towers • Baseline Rev 1.0", font=font_small, fill=COLOR_TEXT_MUTED)
    
    # Progress Bar line
    progress_ratio = frame_idx / float(TOTAL_FRAMES)
    progress_w = int(WIDTH * progress_ratio)
    draw.rectangle([0, HEIGHT - 4, WIDTH, HEIGHT], fill=(229, 231, 235))
    draw.rectangle([0, HEIGHT - 4, progress_w, HEIGHT], fill=COLOR_PRIMARY)

def render_frame(frame_idx):
    sec = frame_idx / float(FPS)
    img = Image.new("RGB", (WIDTH, HEIGHT), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    # ── SCENE 1: THE DISCOVERY (0.0s – 6.0s | Frames 0 – 144) ────────────────
    if frame_idx < 144:
        draw_top_nav(draw, sec)
        draw_bottom_bar(draw, frame_idx, "Scene 1: Introduction & The Core Problem")
        
        # Pill badge
        draw.rounded_rectangle([50, 95, 340, 125], radius=6, fill=COLOR_ACCENT_BG, outline=COLOR_BORDER, width=1)
        draw.text((62, 102), "AI-POWERED PROGRESS GOVERNANCE", font=font_small_bold, fill=COLOR_PRIMARY_DARK)
        
        # Big Headline
        draw.text((50, 140), "Stop Subjective Construction Progress.", font=font_title, fill=COLOR_TEXT_BLACK)
        draw.text((50, 185), "One Master Schedule. Two Independent Streams of Truth.", font=font_heading, fill=COLOR_PRIMARY)
        
        # Two Comparison Cards
        card_w, card_h = 560, 360
        y_card = 245
        
        # Card 1: Traditional
        draw.rounded_rectangle([50, y_card, 50 + card_w, y_card + card_h], radius=12, fill=(255, 255, 255), outline=(229, 231, 235), width=2)
        draw.rectangle([50, y_card, 50 + card_w, y_card + 45], fill=(243, 244, 246))
        draw.text((70, y_card + 12), "Traditional Construction Monitoring", font=font_subtitle, fill=(107, 114, 128))
        
        trad_points = [
            "- Disconnected Excel spreadsheets with human bias",
            "- Contractor reports automatically become project progress",
            "- Zero verification between camera photos and schedule",
            "- Progress disputes, billing delays, and surprise slippage",
            "- Delayed snagging detection causing rework costs"
        ]
        for i, pt in enumerate(trad_points):
            draw.text((70, y_card + 65 + i * 52), pt, font=font_body, fill=COLOR_TEXT_MUTED)
            
        # Card 2: PyCray_SiteIQ
        draw.rounded_rectangle([660, y_card, 660 + card_w, y_card + card_h], radius=12, fill=(248, 250, 255), outline=COLOR_BORDER_STRONG, width=2)
        draw.rectangle([660, y_card, 660 + card_w, y_card + 45], fill=COLOR_PRIMARY)
        draw.text((680, y_card + 12), "PyCray_SiteIQ Dual-Truth Architecture", font=font_subtitle, fill=COLOR_TEXT_WHITE)
        
        iq_points = [
            "v Strict L4 Schedule Reference Baseline (100% Weight)",
            "v Mode A: Fixed Site Cameras run Autonomous AI Vision",
            "v Mode B: Field Photos verified by Google Gemini Vision",
            "v Human-in-the-Loop: Project Manager approves certified qty",
            "v Discrepancy Sentinel: Flags AI vs PM variance > 5%"
        ]
        for i, pt in enumerate(iq_points):
            draw.text((680, y_card + 65 + i * 52), pt, font=font_body_bold, fill=COLOR_TEXT_BLACK)

    # ── SCENE 2: L4 BASELINE & MODE A (6.0s – 12.0s | Frames 144 – 288) ──────
    elif frame_idx < 288:
        draw_top_nav(draw, sec)
        draw_bottom_bar(draw, frame_idx, "Scene 2: Master L4 Baseline & Mode A Autonomous AI")
        
        # Pill badge
        draw.rounded_rectangle([50, 95, 360, 125], radius=6, fill=COLOR_ACCENT_BG, outline=COLOR_BORDER, width=1)
        draw.text((62, 102), "STEP 1: L4 SCHEDULE & MODE A AUTONOMOUS", font=font_small_bold, fill=COLOR_PRIMARY_DARK)
        
        draw.text((50, 140), "L4 Schedule Ingestion & Live Site Vision", font=font_title, fill=COLOR_TEXT_BLACK)
        
        # Left Card: Schedule Parser
        draw.rounded_rectangle([50, 200, 610, 620], radius=12, fill=(255, 255, 255), outline=COLOR_BORDER, width=2)
        draw.text((75, 220), "Master L4 Schedule Baseline Engine", font=font_heading, fill=COLOR_PRIMARY)
        draw.text((75, 255), "BuildTrack_L4_Master_Schedule.xlsx", font=font_body_bold, fill=COLOR_TEXT_MUTED)
        
        specs = [
            ("Canonical Columns", "68 Attributes (WBS, Trade, BOQ, Qty)"),
            ("Activities Ingested", "311 Granular Site Activities"),
            ("WBS Weight Validation", "100.0000% Sum Verified [PASSED]"),
            ("Duplicate ID Checks", "Zero Duplicates / Zero Broken Links"),
            ("Baseline Status", "Rev 1.0 CONFIRMED Active")
        ]
        for i, (k, v) in enumerate(specs):
            y_s = 295 + i * 60
            draw.rectangle([75, y_s, 585, y_s + 45], fill=(248, 250, 255), outline=COLOR_BORDER, width=1)
            draw.text((88, y_s + 12), k, font=font_body_bold, fill=COLOR_TEXT_BLACK)
            draw.text((310, y_s + 12), v, font=font_body, fill=COLOR_PRIMARY_DARK)
            
        # Right Card: Mode A Fixed Cameras
        draw.rounded_rectangle([660, 200, 1220, 620], radius=12, fill=(248, 250, 255), outline=COLOR_BORDER_STRONG, width=2)
        draw.text((685, 220), "Mode A — Fixed Camera AI Vision", font=font_heading, fill=COLOR_PRIMARY)
        draw.text((685, 255), "Continuous Edge Evaluation • Zero Human Sign-Off Needed", font=font_body, fill=COLOR_TEXT_MUTED)
        
        # Simulated Camera Viewfinder
        draw.rounded_rectangle([685, 290, 1195, 470], radius=8, fill=(240, 245, 255), outline=COLOR_PRIMARY, width=2)
        draw.text((705, 305), "CAM-T01-12 | Tower A Level 12 North Deck", font=font_body_bold, fill=COLOR_TEXT_BLACK)
        
        # Simulated bounding box detection
        draw.rectangle([715, 340, 920, 440], outline=COLOR_PRIMARY, width=2)
        draw.text((725, 345), "[DETECTION: Slab Rebar & Deck]", font=font_small_bold, fill=COLOR_PRIMARY)
        draw.text((725, 365), "Observable Progress: 76.0%", font=font_small, fill=COLOR_TEXT_BLACK)
        draw.text((725, 385), "Delta Change: +12.0%", font=font_small, fill=COLOR_GREEN)
        
        draw.rectangle([940, 340, 1175, 440], outline=(16, 185, 129), width=2)
        draw.text((950, 345), "[PPE SENTINEL SCAN]", font=font_small_bold, fill=(16, 185, 129))
        draw.text((950, 365), "Hardhat Compliance: 100%", font=font_small, fill=COLOR_TEXT_BLACK)
        draw.text((950, 385), "Perimeter Netting: DETECTED", font=font_small, fill=COLOR_TEXT_BLACK)
        
        draw.text((685, 495), "Key Spec Rule (§6):", font=font_body_bold, fill=COLOR_PRIMARY)
        draw.text((685, 520), "Camera observations update Mode A Automated Progress directly.", font=font_body, fill=COLOR_TEXT_BLACK)
        draw.text((685, 545), "Provides an untampered baseline of what physical cameras see.", font=font_body, fill=COLOR_TEXT_BLACK)

    # ── SCENE 3: MODE B & GEMINI (12.0s – 18.0s | Frames 288 – 432) ──────────
    elif frame_idx < 432:
        draw_top_nav(draw, sec)
        draw_bottom_bar(draw, frame_idx, "Scene 3: Mode B Field Capture & Google Gemini Vision")
        
        # Pill badge
        draw.rounded_rectangle([50, 95, 380, 125], radius=6, fill=COLOR_ACCENT_BG, outline=COLOR_BORDER, width=1)
        draw.text((62, 102), "STEP 2: MODE B FIELD CAPTURE & AI VALIDATION", font=font_small_bold, fill=COLOR_PRIMARY_DARK)
        
        draw.text((50, 140), "Field Photo Verification with Google Gemini", font=font_title, fill=COLOR_TEXT_BLACK)
        
        # Left Card: Operator Submission
        draw.rounded_rectangle([50, 200, 580, 620], radius=12, fill=(255, 255, 255), outline=COLOR_BORDER, width=2)
        draw.text((75, 220), "Field Operator Site Photo Upload", font=font_heading, fill=COLOR_PRIMARY)
        draw.text((75, 255), "Location: Tower A Level 5 (Internal AAC Masonry)", font=font_body, fill=COLOR_TEXT_MUTED)
        
        op_data = [
            ("Selected Activity", "ACT-L05-MAS-001 Blockwork"),
            ("Captured By", "Kunal Verma (Field Operator)"),
            ("Operator Measured Qty", "125.0 m2 (Tape Measurement)"),
            ("Operator Remarks", "AAC blockwork living room complete"),
            ("Status", "Submitted for AI Quality Verification")
        ]
        for i, (k, v) in enumerate(op_data):
            y_o = 295 + i * 58
            draw.rectangle([75, y_o, 555, y_o + 45], fill=(248, 250, 255), outline=COLOR_BORDER, width=1)
            draw.text((88, y_o + 12), k, font=font_body_bold, fill=COLOR_TEXT_BLACK)
            draw.text((285, y_o + 12), v, font=font_body, fill=COLOR_PRIMARY_DARK)
            
        # Right Card: Gemini Vision Engine
        draw.rounded_rectangle([630, 200, 1220, 620], radius=12, fill=(248, 250, 255), outline=COLOR_BORDER_STRONG, width=2)
        draw.text((655, 220), "Google Gemini Multimodal Vision Evaluation", font=font_heading, fill=COLOR_PRIMARY)
        draw.text((655, 255), "Live Model: gemini-flash-latest with L4 Schedule Context", font=font_body_bold, fill=COLOR_PRIMARY_DARK)
        
        gemini_checks = [
            ("Authentic Construction Site", "DETECTED [PASSED ✓]", COLOR_GREEN),
            ("Unrelated Object / Selfie Check", "REJECTED [PASSED ✓]", COLOR_GREEN),
            ("Activity Context Alignment", "VERIFIED (AAC Blocks Match) ✓", COLOR_GREEN),
            ("Gemini Visual Progress Estimate", "70.0% Completion", COLOR_PRIMARY),
            ("Confidence Rating", "94% AI Confidence Score", COLOR_PRIMARY),
            ("Next Workflow Step", "Queued for Project Manager Review", COLOR_TEXT_BLACK)
        ]
        for i, (k, v, col) in enumerate(gemini_checks):
            y_g = 295 + i * 50
            draw.rectangle([655, y_g, 1195, y_g + 40], fill=(255, 255, 255), outline=COLOR_BORDER, width=1)
            draw.text((670, y_g + 10), k, font=font_body_bold, fill=COLOR_TEXT_BLACK)
            draw.text((950, y_g + 10), v, font=font_body_bold, fill=col)

    # ── SCENE 4: PM REVIEW & 4-WAY TRUTH (18.0s – 24.0s | Frames 432 – 576) ──
    elif frame_idx < 576:
        draw_top_nav(draw, sec)
        draw_bottom_bar(draw, frame_idx, "Scene 4: PM Review Queue & 4-Way Progress Dashboard")
        
        # Pill badge
        draw.rounded_rectangle([50, 95, 380, 125], radius=6, fill=COLOR_ACCENT_BG, outline=COLOR_BORDER, width=1)
        draw.text((62, 102), "STEP 3: PM APPROVAL & 4-WAY COMPARISON", font=font_small_bold, fill=COLOR_PRIMARY_DARK)
        
        draw.text((50, 140), "Human-in-the-Loop & The 4 Progress Streams", font=font_title, fill=COLOR_TEXT_BLACK)
        
        # 4 Hero KPI Cards Row
        kpis = [
            ("Planned Target", "50.15%", "L4 Baseline Schedule", (59, 130, 246)),
            ("Mode A (AI Cameras)", "49.86%", "Autonomous Static Feed", COLOR_PRIMARY),
            ("Mode B (Field Obs)", "50.10%", "Operator Tape Qty", (30, 58, 138)),
            ("Mode B (PM Approved)", "49.27%", "Official Verified Qty", COLOR_TEXT_BLACK),
        ]
        kpi_w = 270
        for i, (title, val, sub, col) in enumerate(kpis):
            x_k = 50 + i * (kpi_w + 25)
            draw.rounded_rectangle([x_k, 200, x_k + kpi_w, 310], radius=10, fill=(255, 255, 255), outline=col, width=2)
            draw.text((x_k + 15, 212), title, font=font_small_bold, fill=COLOR_TEXT_MUTED)
            draw.text((x_k + 15, 235), val, font=font_kpi_num, fill=col)
            draw.text((x_k + 15, 280), sub, font=font_small, fill=COLOR_TEXT_BLACK)
            
        # Lower Section: PM Review Action + Discrepancy Sentinel
        draw.rounded_rectangle([50, 335, 620, 620], radius=12, fill=(248, 250, 255), outline=COLOR_BORDER, width=2)
        draw.text((75, 355), "PM Review Queue (Human-in-the-Loop)", font=font_heading, fill=COLOR_PRIMARY)
        draw.text((75, 390), "Er. Robert Vance (Project Manager) reviews evidence:", font=font_body_bold, fill=COLOR_TEXT_BLACK)
        
        # Action Buttons
        draw.rounded_rectangle([75, 430, 260, 475], radius=6, fill=COLOR_PRIMARY)
        draw.text((100, 442), "✓ APPROVE (120 m2)", font=font_small_bold, fill=COLOR_TEXT_WHITE)
        
        draw.rounded_rectangle([280, 430, 450, 475], radius=6, fill=(255, 255, 255), outline=COLOR_PRIMARY, width=1)
        draw.text((295, 442), "✎ MODIFY QTY", font=font_small_bold, fill=COLOR_PRIMARY)
        
        draw.rounded_rectangle([470, 430, 590, 475], radius=6, fill=(255, 255, 255), outline=(220, 38, 38), width=1)
        draw.text((490, 442), "✕ REJECT", font=font_small_bold, fill=(220, 38, 38))
        
        draw.text((75, 500), "• Approving establishes certified official progress", font=font_body, fill=COLOR_TEXT_BLACK)
        draw.text((75, 530), "• Full audit trail with override reasoning preserved", font=font_body, fill=COLOR_TEXT_BLACK)
        draw.text((75, 560), "• Prevents contractor inflation without physical proof", font=font_body_bold, fill=COLOR_PRIMARY_DARK)
        
        # Right Lower: Discrepancy Sentinel
        draw.rounded_rectangle([660, 335, 1220, 620], radius=12, fill=(255, 255, 255), outline=COLOR_BORDER_STRONG, width=2)
        draw.text((685, 355), "Discrepancy Sentinel & S-Curve", font=font_heading, fill=COLOR_PRIMARY)
        draw.text((685, 390), "Autonomous variance alert comparing AI vs PM:", font=font_body, fill=COLOR_TEXT_MUTED)
        
        # Discrepancy Card
        draw.rectangle([685, 430, 1195, 510], fill=(240, 248, 255), outline=COLOR_BORDER, width=1)
        draw.text((700, 442), "Tower A Level 12 Slab Reinforcement (ACT-TOWA-L12-SLAB)", font=font_body_bold, fill=COLOR_TEXT_BLACK)
        draw.text((700, 472), "AI Observable: 76.0%  |  PM Approved: 72.0%  |  Variance: +4.0%", font=font_body_bold, fill=COLOR_PRIMARY)
        
        draw.text((685, 535), "✓ Automatically flags discrepancies greater than 5%", font=font_body_bold, fill=COLOR_GREEN)
        draw.text((685, 565), "✓ S-Curve plots all 4 streams across the project timeline", font=font_body, fill=COLOR_TEXT_BLACK)

    # ── SCENE 5: OUTRO & CALL TO ACTION (24.0s – 30.0s | Frames 576 – 720) ───
    else:
        draw_top_nav(draw, sec)
        draw_bottom_bar(draw, frame_idx, "Scene 5: Enterprise Intelligence & Platform Access")
        
        # Centered Climax Card
        draw.rounded_rectangle([140, 130, 1140, 630], radius=16, fill=(248, 250, 255), outline=COLOR_BORDER_STRONG, width=2)
        
        # Big Icon
        draw.rounded_rectangle([580, 160, 700, 280], radius=16, fill=COLOR_PRIMARY)
        draw.text((615, 190), "IQ", font=font_title, fill=COLOR_TEXT_WHITE)
        
        draw.text((450, 310), "PyCray_SiteIQ", font=font_title, fill=COLOR_TEXT_BLACK)
        draw.text((375, 360), "Where Construction Meets Precision AI", font=font_heading, fill=COLOR_PRIMARY)
        
        features_row = [
            "• Dual-Truth Engine",
            "• L4 Schedule Sync",
            "• Google Gemini Vision",
            "• PM Review Governance",
            "• Discrepancy Sentinel"
        ]
        draw.text((270, 420), "    ".join(features_row), font=font_body_bold, fill=COLOR_TEXT_BLACK)
        
        # URL Banner
        draw.rounded_rectangle([340, 470, 940, 535], radius=8, fill=COLOR_PRIMARY)
        draw.text((380, 488), "LIVE PLATFORM: http://127.0.0.1:8080", font=font_heading, fill=COLOR_TEXT_WHITE)
        
        draw.text((440, 565), "Grand Horizon Residential Towers • Baseline Rev 1.0", font=font_body, fill=COLOR_TEXT_MUTED)

    return np.array(img)

def generate_video():
    # 1. Ensure Narration Audio Exists
    audio_file = "narration.wav"
    if not os.path.exists(audio_file):
        from create_audio import generate_voiceover_audio
        generate_voiceover_audio(audio_file)
        
    silent_mp4 = "static/temp_silent_video.mp4"
    final_mp4 = "static/PyCray_SiteIQ_30s_Product_Video.mp4"
    os.makedirs("static", exist_ok=True)
    
    print(f"Generating 30s video ({TOTAL_FRAMES} frames at {FPS} FPS)...")
    writer = imageio.get_writer(silent_mp4, fps=FPS, format='FFMPEG', codec='libx264', macro_block_size=16)
    
    for f in range(TOTAL_FRAMES):
        if f % 120 == 0:
            print(f"  Rendering frame {f}/{TOTAL_FRAMES} ({f // FPS}s)...")
        frame_rgb = render_frame(f)
        writer.append_data(frame_rgb)
        
    writer.close()
    print("Silent video rendered successfully.")
    
    # 2. Merge Video and Audio using Bundled FFmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"Merging audio and video using {ffmpeg_exe}...")
    
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", silent_mp4,
        "-i", audio_file,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        final_mp4
    ]
    subprocess.run(cmd, check=True)
    
    if os.path.exists(silent_mp4):
        os.remove(silent_mp4)
        
    print(f"FINAL PROMO VIDEO CREATED: {final_mp4}")
    print(f"File size: {os.path.getsize(final_mp4)} bytes")

if __name__ == "__main__":
    generate_video()
