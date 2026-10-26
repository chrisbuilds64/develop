"""The stamp's sound as a file, the same synthesis the surface plays (web/src/moments.ts): a sine falling 140 → 48 Hz
in 0.18 s with an 8 ms attack, plus a dry noise top. Written for render.mjs to lay under the video."""
import math, random, struct, sys, wave
rate, n = 48000, int(48000 * 0.32)
out = []
f, phase = 140.0, 0.0
for i in range(n):
    t = i / rate
    f = 140 * (48 / 140) ** min(1, t / 0.18)
    phase += 2 * math.pi * f / rate
    env = min(1, t / 0.008) * math.exp(-max(0, t - 0.008) / 0.06)
    noise = (random.random() * 2 - 1) * max(0, 1 - t / 0.06) ** 3 * 0.33
    out.append(max(-1, min(1, 0.9 * env * math.sin(phase) + noise)))
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(x * 32000)) for x in out))
