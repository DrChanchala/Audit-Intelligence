import os
import subprocess
import wave

def generate_voiceover(output_wav="siteiq_narration.wav", voice_index=1):
    # voice_index 1 is Microsoft Zira, 0 is David
    vbs_content = f'''Set voice = CreateObject("SAPI.SpVoice")
Set stream = CreateObject("SAPI.SpFileStream")
stream.Open "{output_wav}", 3, False
Set voice.AudioOutputStream = stream
voice.Rate = 0
Set voice.Voice = voice.GetVoices.Item({voice_index})

' Paragraph 1
voice.Speak "Construction progress you can trust."
WScript.Sleep 600

' Paragraph 2
voice.Speak "SiteIQ checks site cameras and field photos against your schedule."
WScript.Sleep 600

' Paragraph 3
voice.Speak "Track progress on the dashboard, and chat with it to get any detail instantly."
WScript.Sleep 600

' Paragraph 4
voice.Speak "AI brings the efficiency you need."
WScript.Sleep 500

stream.Close
'''
    vbs_path = "generate_audio_temp.vbs"
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    subprocess.run(["cscript", "//nologo", vbs_path], check=True)
    if os.path.exists(vbs_path):
        os.remove(vbs_path)

    if os.path.exists(output_wav):
        with wave.open(output_wav, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            print(f"Generated {output_wav}: {duration:.2f} seconds ({frames} frames @ {rate}Hz)")
            return duration
    return 0

if __name__ == "__main__":
    generate_voiceover()
