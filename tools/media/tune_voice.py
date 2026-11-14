import os
import subprocess
import wave

for rate in [-1, 0]:
    vbs = f"""Set voice = CreateObject("SAPI.SpVoice")
Set stream = CreateObject("SAPI.SpFileStream")
stream.Open "test_rate_{rate}.wav", 3, False
Set voice.AudioOutputStream = stream
voice.Rate = {rate}
Set voice.Voice = voice.GetVoices.Item(1)

WScript.Sleep 600
voice.Speak "Construction progress you can trust."
WScript.Sleep 1000
voice.Speak "SiteIQ checks site cameras and field photos against your schedule."
WScript.Sleep 1000
voice.Speak "Track progress on the dashboard,"
WScript.Sleep 600
voice.Speak "and chat with it to get any detail instantly."
WScript.Sleep 1000
voice.Speak "AI brings the efficiency you need."
WScript.Sleep 1200

stream.Close
"""
    with open("test_vbs.vbs", "w", encoding="utf-8") as f:
        f.write(vbs)
    subprocess.run(["cscript", "//nologo", "test_vbs.vbs"], check=True)
    with wave.open(f"test_rate_{rate}.wav", "rb") as wf:
        print(f"Rate {rate}: {wf.getnframes()/wf.getframerate():.2f}s")

if os.path.exists("test_vbs.vbs"):
    os.remove("test_vbs.vbs")
