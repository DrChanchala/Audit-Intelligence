import subprocess
import os

vbs_code = '''Set voice = CreateObject("SAPI.SpVoice")
For i = 0 To voice.GetVoices.Count - 1
    WScript.Echo i & ": " & voice.GetVoices.Item(i).GetDescription
Next
'''
with open("list_v.vbs", "w", encoding="utf-8") as f:
    f.write(vbs_code)

res = subprocess.run(["cscript", "//nologo", "list_v.vbs"], capture_output=True, text=True)
print("Voices found:\n", res.stdout)
if os.path.exists("list_v.vbs"):
    os.remove("list_v.vbs")
