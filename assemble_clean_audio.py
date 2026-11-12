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

clips = [
    ("clean_clip1.wav", 0.5),
    ("clean_clip2.wav", 10.6),
    ("clean_clip3.wav", 22.4),
    ("clean_clip4.wav", 34.5),
    ("clean_clip5.wav", 46.1),
    ("clean_clip6.wav", 55.8)
]

total_frames = bytearray()
_, nc, sw, fr = read_wav_frames(clips[0][0])

for filename, target_sec in clips:
    c_bytes, _, _, _ = read_wav_frames(filename)
    current_sec = len(total_frames) / (fr * nc * sw)
    if target_sec > current_sec:
        silence_dur = target_sec - current_sec
        total_frames.extend(make_silence(silence_dur, fr, nc, sw))
    total_frames.extend(c_bytes)

# Pad to exactly 63.0 seconds
target_total_sec = 63.0
current_sec = len(total_frames) / (fr * nc * sw)
if target_total_sec > current_sec:
    total_frames.extend(make_silence(target_total_sec - current_sec, fr, nc, sw))

output_audio = "siteiq_clean_synced_audio.wav"
with wave.open(output_audio, "wb") as out_wf:
    out_wf.setnchannels(nc)
    out_wf.setsampwidth(sw)
    out_wf.setframerate(fr)
    out_wf.writeframes(total_frames)

final_dur = len(total_frames) / (fr * nc * sw)
print(f"Generated {output_audio}: {final_dur:.2f} seconds.")
