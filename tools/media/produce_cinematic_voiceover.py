import asyncio
import os
import subprocess
import wave
import edge_tts
import imageio_ffmpeg

VOICE = "en-US-ChristopherNeural"

# Carefully punctuated text to achieve deliberate cadence, natural breathing, and cinematic weight
NARRATION_TEXT = """Every construction project has a plan.

But between schedules, site teams, inspections, and reports, one question matters most: What is actually happening on site... right now?

Introducing Site I Q — AI-powered construction intelligence that turns site evidence into trusted project decisions.

It starts with the construction schedule. Site I Q connects the W B S and L four baseline with actual site activities, creating a reliable foundation for monitoring progress against plan.

Then, intelligence moves to the field. Fixed cameras continuously capture construction activity while AI vision evaluates visible progress. Field teams add photographs, observations, and measured quantities directly against scheduled activities.

Two independent verification streams. One connected view of construction progress.

And AI does not decide the truth alone. Evidence moves through a controlled verification workflow, creating a traceable connection between what was planned, what was observed, and what has been approved.

Site I Q brings planned progress, AI-observed progress, field-observed progress, and project-manager-approved progress together — in one four-stream truth dashboard.

Discrepancies become visible. Risks surface earlier. Teams can identify where construction is diverging from plan, before small issues become major delays.

Site I Q also turns connected project information into answers.
Ask what is delayed.
Ask where progress differs from plan.
Ask what requires review.
Generate daily project intelligence from the same trusted environment.

From planning to progress tracking.
From site evidence to management decisions.
Site I Q creates a continuous, traceable, intelligent verification process.

So owners, contractors, consultants, and project managers don't just see reported progress...

They see verified progress.

Site I Q. Construction progress you can trust."""

async def main():
    os.makedirs("static", exist_ok=True)
    temp_mp3 = "static/temp_cinematic.mp3"
    final_mp3 = "static/SiteIQ_Narration_Cinematic.mp3"
    final_wav = "static/SiteIQ_Narration_Cinematic.wav"

    print(f"Synthesizing voiceover with {VOICE} (rate='-4%', pitch='-1Hz')...")
    communicate = edge_tts.Communicate(
        text=NARRATION_TEXT,
        voice=VOICE,
        rate="-4%",
        pitch="-1Hz"
    )
    await communicate.save(temp_mp3)

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Re-encode MP3 with high-quality CBR 256k stereo
    cmd_mp3 = [
        ffmpeg_exe, "-y",
        "-i", temp_mp3,
        "-b:a", "256k",
        "-ar", "44100",
        final_mp3
    ]
    subprocess.run(cmd_mp3, check=True)

    # Encode Broadcast Studio WAV (48kHz 16-bit PCM Stereo)
    cmd_wav = [
        ffmpeg_exe, "-y",
        "-i", temp_mp3,
        "-ar", "48000",
        "-ac", "2",
        final_wav
    ]
    subprocess.run(cmd_wav, check=True)

    if os.path.exists(temp_mp3):
        os.remove(temp_mp3)

    with wave.open(final_wav, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        duration = frames / float(rate)
        mins = int(duration // 60)
        secs = int(duration % 60)
        print(f"SUCCESS!")
        print(f"  MP3 File : {final_mp3} ({os.path.getsize(final_mp3)} bytes)")
        print(f"  WAV File : {final_wav} ({os.path.getsize(final_wav)} bytes)")
        print(f"  Duration : {duration:.2f} seconds ({mins}m {secs}s)")

if __name__ == "__main__":
    asyncio.run(main())
