#!/usr/bin/env python3
"""Generate a royalty-free ambient music bed (no downloads, pure numpy) for the explainer video.

Usage: python make_music.py DURATION_SECONDS OUT.wav [--mood calm|upbeat|tech] [--seed N]

Why generated: it removes licensing worries and works offline. It is a soft pad + gentle plucks + bass,
meant to sit quietly under captions/voiceover (the renderer mixes it at low volume).
"""
import argparse
import wave

import numpy as np

SR = 44100
MOODS = {
    #            bpm, chord roots (MIDI), minor?, arp density
    "calm":   dict(bpm=84,  prog=[(57, 1), (53, 0), (48, 0), (55, 0)], arp=2, pluck=.30),
    "upbeat": dict(bpm=112, prog=[(48, 0), (55, 0), (57, 1), (53, 0)], arp=4, pluck=.40),
    "tech":   dict(bpm=100, prog=[(50, 1), (46, 0), (53, 0), (48, 0)], arp=4, pluck=.34),
}


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def tone(freq, dur, harm=(1, .5, .25, .12), detune=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * freq * (k + 1) * (1 + detune) * t) for k, a in enumerate(harm))
    return y


def reverb(x, secs=1.8, mix=.28, seed=0):
    rng = np.random.default_rng(seed)
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 6, n))
    ir[:int(.012 * SR)] *= np.linspace(0, 1, int(.012 * SR))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    out = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)]
    out /= (np.max(np.abs(out)) + 1e-9)
    return x * (1 - mix) + out * np.max(np.abs(x)) * mix


def build(duration, mood="calm", seed=7):
    cfg = MOODS[mood]
    rng = np.random.default_rng(seed)
    beat = 60.0 / cfg["bpm"]
    bar = beat * 4
    total = int((duration + 3) * SR)
    L = np.zeros(total)
    R = np.zeros(total)

    def add(sig, start, pan=0.0, gain=1.0):
        i = int(start * SR)
        if i >= total:
            return
        sig = sig[: total - i] * gain
        L[i:i + len(sig)] += sig * (1 - max(0, pan))
        R[i:i + len(sig)] += sig * (1 + min(0, pan))

    nbars = int((duration + 3) / bar) + 1
    for b in range(nbars):
        root, minor = cfg["prog"][b % 4]
        third = 3 if minor else 4
        notes = [root, root + third, root + 7, root + 12]
        t0 = b * bar
        # pad: soft sustained chord, overlapping slightly
        for k, nn in enumerate(notes[:3]):
            for det, pan in ((-.003, -.5), (.003, .5)):
                y = tone(midi(nn + 12), bar + .6, harm=(1, .35, .15), detune=det)
                y *= adsr(len(y), 1.1, 1.2)
                add(y, t0, pan, .055)
        # bass
        y = tone(midi(root - 12), bar, harm=(1, .3))
        y *= adsr(len(y), .02, .5)
        add(y, t0, 0, .20)
        # plucks / arpeggio
        steps = 8 if cfg["arp"] == 2 else 16
        sd = bar / steps
        pattern = [0, 2, 1, 3, 2, 1, 3, 2]
        for s in range(steps):
            if cfg["arp"] == 2 and s % 2 == 1:
                continue
            if rng.random() < .12:
                continue
            nn = notes[pattern[s % len(pattern)]] + 12 + (12 if (s % 8) == 5 else 0)
            y = tone(midi(nn), 1.0, harm=(1, .4, .2, .1))
            y *= np.exp(-np.linspace(0, 7, len(y))) * adsr(len(y), .004, 0)
            add(y, t0 + s * sd, rng.uniform(-.6, .6), cfg["pluck"] * .22)

    st = np.stack([L, R], axis=1)
    st = np.stack([reverb(st[:, 0], seed=1), reverb(st[:, 1], seed=2)], axis=1)
    n = int(duration * SR)
    st = st[:n]
    fi, fo = int(1.5 * SR), int(2.8 * SR)
    st[:fi] *= np.linspace(0, 1, fi)[:, None]
    st[-fo:] *= np.linspace(1, 0, fo)[:, None]
    st /= (np.max(np.abs(st)) + 1e-9)
    return (st * 0.7 * 32767).astype(np.int16)


def write_wav(path, data):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("duration", type=float)
    ap.add_argument("out")
    ap.add_argument("--mood", default="calm", choices=list(MOODS))
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    write_wav(a.out, build(a.duration, a.mood, a.seed))
    print("wrote", a.out)
