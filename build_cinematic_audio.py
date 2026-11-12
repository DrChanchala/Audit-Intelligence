import asyncio
import os
import subprocess
import wave
import edge_tts
import imageio_ffmpeg

SSML_TEXT = """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
<voice name="en-US-ChristopherNeural">
<prosody rate="-5%" pitch="-1Hz">

Every construction project has a plan.
<break time="450ms"/>
But between schedules, site teams, inspections, and reports, one question matters most:
<break time="300ms"/>
<emphasis level="moderate">what is actually happening on site, right now?</emphasis>
<break time="850ms"/>

Introducing Site I Q
<break time="350ms"/>
— AI-powered construction intelligence that turns site evidence into trusted project decisions.
<break time="800ms"/>

It starts with the construction schedule.
<break time="400ms"/>
Site I Q connects the W B S and L four baseline with actual site activities, creating a reliable foundation for monitoring progress against plan.
<break time="800ms"/>

Then, intelligence moves to the field.
<break time="450ms"/>
Fixed cameras continuously capture construction activity while AI vision evaluates visible progress.
<break time="400ms"/>
Field teams add photographs, observations, and measured quantities directly against scheduled activities.
<break time="800ms"/>

<emphasis level="strong">Two independent verification streams.</emphasis>
<break time="450ms"/>
<emphasis level="strong">One connected view of construction progress.</emphasis>
<break time="850ms"/>

And AI does not decide the truth alone.
<break time="450ms"/>
Evidence moves through a controlled verification workflow, creating a traceable connection between what was planned, what was observed, and what has been approved.
<break time="800ms"/>

Site I Q brings planned progress, AI-observed progress, field-observed progress, and project-manager-approved progress together
<break time="300ms"/>
in one <emphasis level="strong">four-stream truth dashboard</emphasis>.
<break time="850ms"/>

<emphasis level="moderate">Discrepancies become visible.</emphasis>
<break time="400ms"/>
<emphasis level="moderate">Risks surface earlier.</emphasis>
<break time="450ms"/>
Teams can identify where construction is diverging from plan
<break time="300ms"/>
before small issues become major delays.
<break time="850ms"/>

Site I Q also turns connected project information into answers.
<break time="450ms"/>
Ask what is delayed.
<break time="350ms"/>
Ask where progress differs from plan.
<break time="350ms"/>
Ask what requires review.
<break time="450ms"/>
Generate daily project intelligence from the same trusted environment.
<break time="850ms"/>

From planning to progress tracking.
<break time="400ms"/>
From site evidence to management decisions.
<break time="450ms"/>
Site I Q creates a continuous, traceable, intelligent verification process.
<break time="850ms"/>

So owners, contractors, consultants, and project managers don't just see reported progress.
<break time="550ms"/>
<emphasis level="strong">They see verified progress.</emphasis>
<break time="1000ms"/>

Site I Q.
<break time="400ms"/>
<emphasis level="strong">Construction progress you can trust.</emphasis>

</prosody>
</voice>
</speak>"""

async def generate():
    os.makedirs("static", exist_ok=True)
    mp3_path = "static/SiteIQ_Narration_Cinematic.mp3"
    wav_path = "static/SiteIQ_Narration_Cinematic.wav"

    print("Synthesizing neural cinematic voiceover with en-US-ChristopherNeural...")
    communicate = edge_tts.Communicate(SSML_TEXT, "en-US-ChristopherNeural")
    await communicate.save(mp3_path)
    print(f"Saved MP3: {mp3_path} ({os.path.getsize(mp3_path)} bytes)")

    # Convert to high-fidelity 48kHz stereo WAV for studio usage
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", mp3_path,
        "-ar", "48000",
        "-ac", "2",
        wav_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Saved Studio WAV: {wav_path} ({os.path.getsize(wav_path)} bytes)")

    with wave.open(wav_path, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        duration = frames / float(rate)
        print(f"Total Audio Duration: {duration:.2f} seconds ({int(duration // 60)}m {int(duration % 60)}s)")

if __name__ == "__main__":
    asyncio.run(generate())
