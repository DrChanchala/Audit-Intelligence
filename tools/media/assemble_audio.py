import wave
import struct

def make_silence(duration_sec, sample_rate=22050, n_channels=1, sampwidth=2):
    num_samples = int(duration_sec * sample_rate)
    return b'\x00' * (num_samples * n_channels * sampwidth)

def read_wav_frames(filename):
    with wave.open(filename, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        return frames, n_channels, sampwidth, framerate

# Timeline plan (in seconds):
# 0.0s - 0.4s: Silence (0.4s)
# 0.4s - ~3.24s: Clip 1 (2.84s) -> "Construction progress you can trust."
# ~3.24s - 3.8s: Silence (0.56s)
# 3.8s - ~8.53s: Clip 2 (4.73s) -> "SiteIQ checks site cameras and field photos against your schedule."
# ~8.53s - 9.4s: Silence (0.87s)
# 9.4s - ~11.96s: Clip 3 (2.56s) -> "Track progress on the dashboard,"
# ~11.96s - 12.6s: Silence (0.64s)
# 12.6s - ~15.78s: Clip 4 (3.18s) -> "and chat with it to get any detail instantly."
# ~15.78s - 16.5s: Silence (0.72s)
# 16.5s - ~19.37s: Clip 5 (2.87s) -> "AI brings the efficiency you need."
# ~19.37s - 20.0s: Silence (0.63s outro tail)

c1, nc, sw, fr = read_wav_frames("clip1.wav")
c2, _, _, _ = read_wav_frames("clip2.wav")
c3, _, _, _ = read_wav_frames("clip3.wav")
c4, _, _, _ = read_wav_frames("clip4.wav")
c5, _, _, _ = read_wav_frames("clip5.wav")

total_frames = bytearray()

def append_clip(clip_bytes, target_start_sec):
    global total_frames
    current_sec = len(total_frames) / (fr * nc * sw)
    if target_start_sec > current_sec:
        silence_dur = target_start_sec - current_sec
        total_frames.extend(make_silence(silence_dur, fr, nc, sw))
    total_frames.extend(clip_bytes)

append_clip(c1, 0.4)
append_clip(c2, 3.8)
append_clip(c3, 9.4)
append_clip(c4, 12.6)
append_clip(c5, 16.5)

# Pad to exactly 20.0 seconds
target_total_sec = 20.0
current_sec = len(total_frames) / (fr * nc * sw)
if target_total_sec > current_sec:
    total_frames.extend(make_silence(target_total_sec - current_sec, fr, nc, sw))

with wave.open("narration_synced.wav", "wb") as out_wf:
    out_wf.setnchannels(nc)
    out_wf.setsampwidth(sw)
    out_wf.setframerate(fr)
    out_wf.writeframes(total_frames)

print(f"Generated narration_synced.wav: {len(total_frames)/(fr*nc*sw):.2f}s total.")
