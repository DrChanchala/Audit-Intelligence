import asyncio
import os
import subprocess
import wave
import edge_tts
import imageio_ffmpeg

VOICE = "en-US-ChristopherNeural"

clips_text = [
    ("neural_clip1", "Construction progress you can trust. Welcome to SiteIQ, the AI-powered intelligence platform for modern construction projects."),
    ("neural_clip2", "Fixed site cameras track progress 24/7 in Mode A, while field teams capture photo evidence with Mode B, verified instantly by Google Gemini AI vision."),
    ("neural_clip3", "Upload your L4 master schedule. The engine validates 311 WBS activities, quantities, and weights to establish your confirmed project baseline."),
    ("neural_clip4", "Track four independent streams on your dashboard: Planned, AI Automated, Field Observed, and PM Approved progress, complete with S-curves and discrepancy alerts."),
    ("neural_clip5", "Chat with the AI Assistant using natural language to query schedule variances, review delays, and generate daily reports instantly."),
    ("neural_clip6", "SiteIQ: Precision, verification, and AI-driven efficiency for your jobsite.")
]

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

async def generate_clips():
    clip_durations = []
    for prefix, text in clips_text:
        mp3_file = f"{prefix}.mp3"
        wav_file = f"{prefix}.wav"
        
        # Rate slightly controlled for clear professional documentary feel (-4%)
        communicate = edge_tts.Communicate(text, VOICE, rate="-4%")
        await communicate.save(mp3_file)
        
        # Convert to 24000Hz 16-bit PCM wav
        cmd = [ffmpeg_exe, "-y", "-i", mp3_file, "-ar", "24000", "-ac", "1", wav_file]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        with wave.open(wav_file, 'rb') as wf:
            dur = wf.getnframes() / float(wf.getframerate())
            clip_durations.append((wav_file, dur, text))
            print(f"{wav_file}: {dur:.2f}s -> {text[:45]}...")
            
    return clip_durations

def make_silence(duration_sec, sample_rate=24000, n_channels=1, sampwidth=2):
    num_samples = int(duration_sec * sample_rate)
    return b'\x00' * (num_samples * n_channels * sampwidth)

def read_wav_frames(filename):
    with wave.open(filename, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        return frames, n_channels, sampwidth, framerate

def assemble_timeline(clip_durations):
    # Calculate scene start times with natural padding
    # Scene 1: 0.0 to T1
    # Scene 2: T1 to T2
    # etc.
    lead_in = 0.5
    pause = 0.8
    
    total_frames = bytearray()
    _, nc, sw, fr = read_wav_frames(clip_durations[0][0])
    
    scene_timings = []
    cur_time = 0.0
    
    for idx, (filename, dur, text) in enumerate(clip_durations):
        scene_start = cur_time
        speech_start = scene_start + (lead_in if idx == 0 else 0.4)
        
        current_audio_time = len(total_frames) / (fr * nc * sw)
        if speech_start > current_audio_time:
            total_frames.extend(make_silence(speech_start - current_audio_time, fr, nc, sw))
            
        c_bytes, _, _, _ = read_wav_frames(filename)
        total_frames.extend(c_bytes)
        
        cur_time = speech_start + dur + pause
        scene_timings.append((scene_start, cur_time, dur, text))
        
    final_dur = round(cur_time + 0.5, 1) # add a clean 0.5s outro tail
    
    # Pad to final_dur
    current_audio_time = len(total_frames) / (fr * nc * sw)
    if final_dur > current_audio_time:
        total_frames.extend(make_silence(final_dur - current_audio_time, fr, nc, sw))
        
    out_wav = "siteiq_neural_synced_audio.wav"
    with wave.open(out_wav, "wb") as out_wf:
        out_wf.setnchannels(nc)
        out_wf.setsampwidth(sw)
        out_wf.setframerate(fr)
        out_wf.writeframes(total_frames)
        
    print(f"\nFinal Neural Audio: {out_wav} ({final_dur:.2f}s total duration)")
    for i, (st, et, d, t) in enumerate(scene_timings, 1):
        print(f"  Scene {i}: {st:.2f}s -> {et:.2f}s (speech {d:.2f}s)")
        
    return scene_timings, final_dur

if __name__ == "__main__":
    durations = asyncio.run(generate_clips())
    assemble_timeline(durations)
