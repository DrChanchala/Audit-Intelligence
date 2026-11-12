import os
import subprocess
import wave

clips = [
    ("clean_clip1.wav", "Construction progress you can trust. Welcome to SiteIQ, the AI-powered intelligence platform for modern construction projects."),
    ("clean_clip2.wav", "Fixed site cameras track progress 24/7 in Mode A, while field teams capture photo evidence with Mode B, verified instantly by Google Gemini AI vision."),
    ("clean_clip3.wav", "Upload your L4 master schedule. The engine validates 311 WBS activities, quantities, and weights to establish your confirmed project baseline."),
    ("clean_clip4.wav", "Track four independent streams on your dashboard: Planned, AI Automated, Field Observed, and PM Approved progress, complete with S-curves and discrepancy alerts."),
    ("clean_clip5.wav", "Chat with the AI Assistant using natural language to query schedule variances, review delays, and generate daily reports instantly."),
    ("clean_clip6.wav", "SiteIQ: Precision, verification, and AI-driven efficiency for your jobsite.")
]

vbs_lines = [
    'Set voice = CreateObject("SAPI.SpVoice")',
    'voice.Rate = 0',
    'Set voice.Voice = voice.GetVoices.Item(1)'  # Microsoft Zira Desktop
]

for filename, text in clips:
    vbs_lines.append(f'Set stream_{filename[:6]} = CreateObject("SAPI.SpFileStream")')
    vbs_lines.append(f'stream_{filename[:6]}.Open "{filename}", 3, False')
    vbs_lines.append(f'Set voice.AudioOutputStream = stream_{filename[:6]}')
    vbs_lines.append(f'voice.Speak "{text}"')
    vbs_lines.append(f'stream_{filename[:6]}.Close')

vbs_code = "\n".join(vbs_lines)
with open("gen_clean_audio.vbs", "w", encoding="utf-8") as f:
    f.write(vbs_code)

subprocess.run(["cscript", "//nologo", "gen_clean_audio.vbs"], check=True)
if os.path.exists("gen_clean_audio.vbs"):
    os.remove("gen_clean_audio.vbs")

clip_durations = []
for filename, text in clips:
    with wave.open(filename, 'rb') as wf:
        dur = wf.getnframes() / float(wf.getframerate())
        clip_durations.append((filename, dur, text))
        print(f"{filename}: {dur:.2f}s -> {text[:45]}...")

total_speech = sum(d for _, d, _ in clip_durations)
print(f"Total pure speech duration: {total_speech:.2f}s")
