import os
import subprocess

def generate_voiceover_audio(output_wav="narration.wav"):
    vbs_content = """Set voice = CreateObject("SAPI.SpVoice")
Set stream = CreateObject("SAPI.SpFileStream")
stream.Open "narration.wav", 3, False
Set voice.AudioOutputStream = stream
voice.Rate = 1
voice.Speak "Traditional construction tracking is slow and subjective. Meet PyCray SiteIQ. Upload your L4 master schedule. Fixed site cameras autonomously track physical progress with zero human intervention. Field operators capture site photos verified in real time by Google Gemini Vision. Project managers approve certified quantities, uniting Planned, AI, and Certified progress. PyCray SiteIQ: Precision AI for Construction."
stream.Close
"""
    vbs_path = "tts_gen.vbs"
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    subprocess.run(["cscript", "//nologo", vbs_path], check=True)
    if os.path.exists(vbs_path):
        os.remove(vbs_path)

    return os.path.exists(output_wav)

if __name__ == "__main__":
    success = generate_voiceover_audio()
    print("Audio Generated:", success)
    if os.path.exists("narration.wav"):
        print("Size in bytes:", os.path.getsize("narration.wav"))
