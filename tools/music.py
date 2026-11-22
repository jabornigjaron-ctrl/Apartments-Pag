#!/usr/bin/env python3
"""Erzeugt eigene, lizenzfreie Hintergrundmusik (sommerlich, entspannt).

Alles wird hier per Synthese berechnet - keine Samples, keine fremden Rechte.
Aufruf: python3 tools/music.py musik/sommer-1.wav --seed 1 --bpm 96 --key 2 --sek 24
Benoetigt: numpy
"""
import argparse, wave
import numpy as np

SR = 44100
PROGS = [  # Akkordfolgen (Halbtoene relativ zur Tonart), je 4 Takte
    [[0, 4, 7, 11], [9, 12, 16, 19], [5, 9, 12, 16], [7, 11, 14, 17]],    # Imaj7 vi7 IVmaj7 V
    [[0, 4, 7, 14], [7, 11, 14, 19], [9, 12, 16, 21], [5, 9, 12, 16]],    # I V vi IV
    [[5, 9, 12, 16], [7, 11, 14, 17], [4, 7, 11, 14], [9, 12, 16, 19]],   # IV V iii vi
]


def hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x); s = 0.0
    for i, v in enumerate(x):
        s = (1 - a) * v + a * s
        y[i] = s
    return y


def env(n, att, rel):
    e = np.ones(n)
    a = min(int(att * SR), n); r = min(int(rel * SR), n - a)
    e[:a] = np.linspace(0, 1, a)
    if r > 0:
        e[n - r:] = np.linspace(1, 0, r)
    return e


def reverb(x, mix=0.25):
    out = x.copy()
    for d, g in [(1557, .62), (1617, .6), (1491, .58), (1422, .57), (1277, .55), (1356, .54)]:
        y = x.copy()
        for k in range(1, 7):
            sh = d * k
            if sh >= len(x):
                break
            y[sh:] += x[:-sh] * g ** k
        out += y * (mix / 6)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--bpm", type=float, default=96)
    ap.add_argument("--key", type=int, default=0, help="Tonart-Verschiebung in Halbtoenen (0=C)")
    ap.add_argument("--sek", type=float, default=24)
    ap.add_argument("--stil", choices=["chill", "house", "lofi", "cinematic"], default="chill")
    a = ap.parse_args()
    if a.stil != "chill":
        return render_style(a)
    rng = np.random.default_rng(a.seed)
    prog = PROGS[a.seed % len(PROGS)]
    beat = 60 / a.bpm
    bar = 4 * beat
    n = int(a.sek * SR)
    t_all = np.arange(n) / SR
    pad = np.zeros(n); pl = np.zeros(n); bass = np.zeros(n); drums = np.zeros(n)
    root = 48 + a.key

    nbars = int(np.ceil(a.sek / bar))
    for b in range(nbars):
        chord = prog[b % 4]
        s0 = int(b * bar * SR); L = min(int(bar * SR), n - s0)
        if L <= 0:
            break
        tt = np.arange(L) / SR
        # weiche Flaechen (leicht verstimmte Saegezaehne, spaeter tiefpassgefiltert)
        seg = np.zeros(L)
        for iv in chord:
            f = hz(root + 12 + iv)
            for det in (-0.12, 0.12):
                ph = (f * 2 ** (det / 12) * tt) % 1.0
                seg += (2 * ph - 1) * 0.05
        pad[s0:s0 + L] += seg * env(L, 0.6, 0.6)
        # Bass: Grundton auf 1 und 3
        for q in (0, 2):
            q0 = s0 + int(q * beat * SR); ql = min(int(beat * 1.8 * SR), n - q0)
            if ql > 0:
                tq = np.arange(ql) / SR
                bass[q0:q0 + ql] += np.sin(2 * np.pi * hz(root - 12 + chord[0]) * tq) * np.exp(-tq * 2.2) * 0.35
        # Marimba-artiges Arpeggio in Achteln
        pattern = rng.permutation(8)
        for e8 in range(8):
            if rng.random() < 0.18:
                continue
            note = root + 24 + chord[pattern[e8] % 4] + (12 if pattern[e8] > 5 else 0)
            p0 = s0 + int(e8 * beat / 2 * SR); plen = min(int(0.9 * SR), n - p0)
            if plen <= 0:
                continue
            tp = np.arange(plen) / SR
            f = hz(note)
            tone = (np.sin(2 * np.pi * f * tp) + 0.25 * np.sin(2 * np.pi * 4 * f * tp) * np.exp(-tp * 30))
            pl[p0:p0 + plen] += tone * np.exp(-tp * 6) * 0.16
        # sanfter Beat: Kick auf 1 und 3, Shaker in Achteln (erst ab Takt 2)
        if b >= 1:
            for q in range(4):
                k0 = s0 + int(q * beat * SR)
                if q in (0, 2):
                    kl = min(int(0.25 * SR), n - k0)
                    tk = np.arange(kl) / SR
                    drums[k0:k0 + kl] += np.sin(2 * np.pi * (50 + 70 * np.exp(-tk * 40)) * tk) * np.exp(-tk * 18) * 0.45
                for h in (0, 1):
                    h0 = k0 + int(h * beat / 2 * SR); hl = min(int(0.06 * SR), n - h0)
                    if hl > 0:
                        nz = rng.standard_normal(hl)
                        nz = nz - np.concatenate([[0], nz[:-1]])  # Hochpass grob
                        drums[h0:h0 + hl] += nz * np.exp(-np.arange(hl) / SR * 60) * (0.018 if h else 0.012)

    pad = lowpass(pad, 1400)
    mix = pad + pl + bass + drums
    mix = reverb(mix, 0.35)
    mix *= env(n, 1.0, 2.5)
    mix = np.tanh(mix * 1.1)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.8
    st = np.stack([mix, np.roll(mix, 220) * 0.97], axis=1)  # leichte Stereobreite
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print("Musik:", a.out)


def noise_hit(rng, n, decay, gain, hp=True):
    nz = rng.standard_normal(n)
    if hp:
        nz = nz - np.concatenate([[0], nz[:-1]])
    return nz * np.exp(-np.arange(n) / SR * decay) * gain


def add(buf, start, sig):
    s = int(start)
    if s >= len(buf):
        return
    e = min(len(buf), s + len(sig))
    buf[s:e] += sig[:e - s]


def kick(gain=0.5, length=0.28):
    t = np.arange(int(length * SR)) / SR
    return np.sin(2 * np.pi * (48 + 90 * np.exp(-t * 35)) * t) * np.exp(-t * 14) * gain


def epiano(f, dur, gain):
    t = np.arange(int(dur * SR)) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 3)
    return tone * np.exp(-t * 1.6) * (1 + 0.15 * np.sin(2 * np.pi * 5 * t)) * gain


def render_style(a):
    """Weitere Stile: house (tanzbar, 4/4), lofi (entspannt, Vinyl), cinematic (ruhig, ohne Beat)."""
    rng = np.random.default_rng(a.seed)
    prog = PROGS[a.seed % len(PROGS)]
    bpm = a.bpm if a.bpm != 96 else {"house": 122, "lofi": 78, "cinematic": 70}[a.stil]
    beat = 60 / bpm; bar = 4 * beat
    n = int(a.sek * SR)
    keys = np.zeros(n); bass = np.zeros(n); drums = np.zeros(n); pad = np.zeros(n)
    root = 48 + a.key
    nbars = int(np.ceil(a.sek / bar))
    for b in range(nbars):
        chord = prog[b % 4]
        s0 = b * bar * SR
        L = int(bar * SR)
        tt = np.arange(L) / SR
        if a.stil == "house":
            # Off-Beat-Akkordstabs, Bass in Achteln auf der Off-Zaehlzeit, Four-on-the-floor
            for q in range(4):
                add(drums, s0 + q * beat * SR, kick(0.55))
                add(drums, s0 + (q + 0.5) * beat * SR, noise_hit(rng, int(0.12 * SR), 35, 0.05))   # offene HiHat
                if q in (1, 3):
                    add(drums, s0 + q * beat * SR, noise_hit(rng, int(0.15 * SR), 28, 0.16, hp=False))  # Clap
                for e in (0.5,):
                    seg = np.zeros(int(0.22 * SR))
                    tq = np.arange(len(seg)) / SR
                    for iv in chord:
                        f = hz(root + 12 + iv)
                        seg += (2 * ((f * tq) % 1.0) - 1) * 0.06
                    add(keys, s0 + (q + e) * beat * SR, lowpass(seg * np.exp(-tq * 14), 2600))
                    tb = np.arange(int(beat * 0.45 * SR)) / SR
                    fb = hz(root - 12 + chord[0])
                    add(bass, s0 + (q + e) * beat * SR,
                        (np.sin(2 * np.pi * fb * tb) + 0.3 * np.sin(4 * np.pi * fb * tb)) * np.exp(-tb * 6) * 0.4)
            add(pad, s0, sum(np.sin(2 * np.pi * hz(root + 24 + iv) * tt) for iv in chord) * 0.012)
        elif a.stil == "lofi":
            for i, iv in enumerate(chord):  # leicht verschleppter E-Piano-Akkord
                add(keys, s0 + i * 0.03 * SR, epiano(hz(root + 12 + iv), bar * 0.95, 0.09))
            add(bass, s0, np.sin(2 * np.pi * hz(root - 12 + chord[0]) * tt) * np.exp(-tt * 1.2) * 0.3)
            swing = 0.62
            for q in range(4):
                if q in (0,) or (q == 2 and rng.random() < 0.5):
                    add(drums, s0 + q * beat * SR, kick(0.42, 0.3))
                if q == 2 and rng.random() >= 0.5:
                    add(drums, s0 + (q + 0.5) * beat * SR, kick(0.35, 0.3))
                if q in (1, 3):
                    add(drums, s0 + q * beat * SR, noise_hit(rng, int(0.18 * SR), 22, 0.10, hp=False))
                for h in (0, swing):
                    add(drums, s0 + (q + h) * beat * SR, noise_hit(rng, int(0.05 * SR), 70, 0.025))
        else:  # cinematic
            seg = np.zeros(L)
            for iv in chord:
                for det in (-0.08, 0.08):
                    f = hz(root + iv) * 2 ** (det / 12)
                    seg += (2 * ((f * tt) % 1.0) - 1) * 0.045
            add(pad, s0, lowpass(seg, 900) * env(L, bar * 0.45, bar * 0.45))
            add(bass, s0, np.sin(2 * np.pi * hz(root - 12 + chord[0]) * tt) * env(L, 0.8, 1.0) * 0.3)
            for k in range(3):  # einzelne Klaviertoene
                note = root + 24 + chord[rng.integers(0, 4)] + (12 if rng.random() < 0.3 else 0)
                tp = np.arange(int(2.5 * SR)) / SR
                add(keys, s0 + (k * 1.3 + rng.random() * 0.4) * beat * SR,
                    (np.sin(2 * np.pi * hz(note) * tp) + 0.2 * np.sin(4 * np.pi * hz(note) * tp)) * np.exp(-tp * 1.8) * 0.12)
            if b % 2 == 1:  # tiefer Schlag alle zwei Takte
                add(drums, s0, kick(0.35, 0.8))
    mix = keys + bass + drums + pad
    if a.stil == "lofi":
        mix = lowpass(mix, 3800)
        crackle = np.zeros(n)
        idx = rng.integers(0, n, size=int(a.sek * 12))
        crackle[idx] = rng.standard_normal(len(idx)) * 0.04
        mix += lowpass(crackle + rng.standard_normal(n) * 0.0006, 5000)
    mix = reverb(mix, {"house": 0.18, "lofi": 0.25, "cinematic": 0.5}[a.stil])
    mix *= env(n, 0.3 if a.stil == "house" else 1.2, 2.0)
    mix = np.tanh(mix * 1.2)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.85
    st = np.stack([mix, np.roll(mix, 260) * 0.97], axis=1)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print("Musik:", a.out, a.stil, f"{bpm:.0f} bpm")


if __name__ == "__main__":
    main()
