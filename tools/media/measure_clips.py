import os
import subprocess
import wave

clips = [
    ("clip1.wav", "Construction progress you can trust."),
    ("clip2.wav", "SiteIQ checks site cameras and field photos against your schedule."),
    ("clip3.wav", "Track progress on the dashboard,"),
    ("clip4.wav", "and chat with it to get any detail instantly."),
    ("clip5.wav", "AI brings the efficiency you need.")
]

vbs_lines = ['Set voice = CreateObject("SAPI.SpVoice")', 'voice.Rate = 0', 'Set voice.Voice = voice.GetVoices.Item(1)']

for filename, text in clips:
    vbs_lines.append(f'Set stream_{filename[:5]} = CreateObject("SAPI.SpFileStream")')
    vbs_lines.append(f'stream_{filename[:5]}.Open "{filename}", 3, False')
    vbs_lines.append(f'Set voice.AudioOutputStream = stream_{filename[:5]}')
    vbs_lines.append(f'voice.Speak "{text}"')
    vbs_lines.append(f'stream_{filename[:5]}.Close')

vbs_code = "\n".join(vbs_lines)
with open("gen_clips.vbs", "w", encoding="utf-8") as f:
    f.write(vbs_code)

subprocess.run(["cscript", "//nologo", "gen_clips.vbs"], check=True)
if os.path.exists("gen_clips.vbs"):
    os.remove("gen_clips.vbs")

durations = []
for filename, text in clips:
    with wave.open(filename, 'rb') as wf:
        dur = wf.getnframes() / float(wf.getframerate())
        durations.append((filename, dur, text))
        print(f"{filename}: {dur:.2f}s -> \"{text}\"")
