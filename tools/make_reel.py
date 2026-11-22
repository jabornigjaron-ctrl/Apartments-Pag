#!/usr/bin/env python3
"""Schneidet aus mehreren Clips ein Reel (1080x1920, 30 fps, H.264).

Aufruf:
  python3 tools/make_reel.py reels/2026-11-12.mp4 --stil bold --uebergang mix \
      --hook "POV: du hast|endlich gebucht" --ende "Sommer 2027|jetzt anfragen" --musik musik/house-1.m4a \
      --zeile "5-8:1. Turkises Wasser" \
      videos/strand-003.mp4:2:3.5 videos/apartments-002.mp4:0:3 fotos/strand-010.jpg::3

Clips:      DATEI:START:DAUER[:FOKUS]  (Sekunden; FOKUS 0.0-1.0 = horizontaler Ausschnitt, 0.5 Mitte).
            Fotos bekommen einen langsamen Zoom. Querformat wird auf 9:16 zugeschnitten.
--stil:     magazin  kleine gesperrte Zeile + grosse kursive Serifenschrift (edel, ruhig)
            bold     grosse Grossbuchstaben (Anton) mit Kontur, gelbe Kickerzeile (laut, viral)
            pov      schwarzer Text auf weissen Balken wie Instagram-Text (nativ, "POV"/Listen)
            hand     Handschrift (Caveat), warm und persoenlich
--uebergang fade | mix (abwechselnd Wischen/Gleiten/Kreis/Zoom) | schnitt (harte Schnitte, schnell)
--zeile     "VON-BIS:Text" (mehrfach) fuer Zwischentexte, z. B. Listen "1. ...", "2. ..."
Texte: "|" = Zeilenumbruch, keine Emojis, keine c-Haken-Buchstaben (ć č š ž) - Schriften koennen sie nicht.
Der Hook steht ab dem ersten Bild (wichtig fuer Reichweite und Vorschaubild).
Ton: --musik DATEI (nur lizenzfreie/eigene Musik); ohne Musik stille Tonspur.
"""
import argparse, random, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
F = ROOT / "tools/fonts"
FONTS = {
    "serif": F / "PlayfairDisplay-MediumItalic.ttf",
    "kicker": F / "Montserrat-SemiBold.ttf",
    "heavy": F / "Montserrat-ExtraBold.ttf",
    "anton": F / "Anton-Regular.ttf",
    "hand": F / "Caveat-Bold.ttf",
}
W, H, FPS = 1080, 1920, 30
MIX = ["smoothleft", "smoothup", "circleopen", "slideleft", "zoomin", "wipeleft", "fade", "smoothright"]


def esc(t):
    # Emojis kann keine der Schriften darstellen -> entfernen
    t = "".join(ch for ch in t if ord(ch) < 0x2190 or ch in "→←").strip()
    t = " ".join(p for p in t.split(" ") if p)  # nur normale Leerzeichen zusammenfassen
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def segment(src, start, dur, focus, out):
    src = str(ROOT / src) if not Path(src).is_absolute() else src
    crop = f"crop={W}:{H}:(iw-{W})*{focus}:(ih-{H})/2"
    if src.lower().endswith((".jpg", ".jpeg", ".png")):
        frames = int(dur * FPS)
        vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
              f"zoompan=z='min(1+0.0015*on,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={W}x{H}:fps={FPS}")
        cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", src, "-t", str(dur), "-vf", vf]
    else:
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,{crop},fps={FPS}"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(dur), "-i", src, "-vf", vf]
    cmd += ["-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", out]
    subprocess.run(cmd, check=True)


def alpha(t0, t1, fin, fout=0.4):
    if fin <= 0:
        return f"if(between(t,{t0:.2f},{t1-fout:.2f}),1,if(between(t,{t1-fout:.2f},{t1:.2f}),({t1:.2f}-t)/{fout},0))"
    return (f"if(lt(t,{t0:.2f}),0,if(lt(t,{t0+fin:.2f}),(t-{t0:.2f})/{fin},"
            f"if(lt(t,{t1-fout:.2f}),1,if(lt(t,{t1:.2f}),({t1:.2f}-t)/{fout},0))))")


def spaced(s):  # Sperrsatz fuer Kickerzeilen
    return " ".join(" " if c == " " else c for c in s.upper())


def fit(lines, sizes):
    m = max(len(l) for l in lines)
    for limit, size in sizes:
        if m <= limit:
            return size
    return sizes[-1][1]


class Style:
    """Liefert drawtext-Filter fuer die Schattenebene (wird weichgezeichnet) und die Vordergrundebene."""

    def __init__(self, name):
        self.name = name
        # Position (y) von Hook, Zwischentext, Ende - und Einblenddauer
        self.y = {"magazin": (330, 1150, 1180), "bold": (520, 1250, 1100),
                  "pov": (420, 1200, 1250), "hand": (380, 1150, 1150)}[name]
        self.fin = {"magazin": 0.5, "bold": 0.0, "pov": 0.0, "hand": 0.4}[name]

    def layers(self, klein, gross, t0, t1, y, small=False):
        fin = 0.0 if t0 < 0.05 else self.fin  # Hook steht sofort im ersten Bild
        al = alpha(t0, t1, fin)
        lines = [l.strip() for l in gross.split("|") if l.strip()]
        sh, fr, yy = [], [], y
        lift = f"+18*max(0\\,1-(t-{t0:.2f})/0.7)" if fin else ""

        def dt(font, text, size, color, extra="", ypos=None):
            return (f"drawtext=fontfile={font}:text='{esc(text)}':fontsize={size}:fontcolor={color}"
                    f":x=(w-tw)/2:y={ypos if ypos is not None else yy}{lift}:alpha='{al}'{extra}")

        k = 0.8 if small and self.name != "bold" else 1.0
        if self.name == "magazin":
            if klein:
                sh.append(dt(FONTS["kicker"], spaced(klein), 34, "black@0.7", ypos=yy + 4))
                fr.append(dt(FONTS["kicker"], spaced(klein), 34, "white"))
                yy += 70
            size = int(fit(lines, [(16, 104), (20, 88), (99, 74)]) * k)
            for l in lines:
                sh.append(dt(FONTS["serif"], l, size, "black@0.7", ypos=yy + 4))
                fr.append(dt(FONTS["serif"], l, size, "white"))
                yy += int(size * 1.18)
        elif self.name == "bold":
            if klein:
                fr.append(dt(FONTS["heavy"], klein.upper(), 40, "0xFFD84D",
                             ":borderw=3:bordercolor=black@0.6"))
                yy += 64
            size = int(fit(lines, [(10, 150), (14, 124), (18, 100), (99, 84)]) * k)
            for l in lines:
                sh.append(dt(FONTS["anton"], l.upper(), size, "black@0.6", ypos=yy + 8))
                fr.append(dt(FONTS["anton"], l.upper(), size, "white", ":borderw=5:bordercolor=black@0.85"))
                yy += int(size * 1.08)
        elif self.name == "pov":
            size = int(fit(lines, [(22, 56), (28, 48), (99, 42)]) * k)
            allines = ([klein] if klein else []) + lines
            for i, l in enumerate(allines):
                s = size if (i or not klein) else int(size * 0.7)
                fr.append(dt(FONTS["kicker"] if i or not klein else FONTS["heavy"], l, s, "black",
                             ":box=1:boxcolor=white@0.96:boxborderw=20"))
                yy += int(s * 1.0) + 44
        elif self.name == "hand":
            if klein:
                sh.append(dt(FONTS["kicker"], spaced(klein), 32, "black@0.7", ypos=yy + 4))
                fr.append(dt(FONTS["kicker"], spaced(klein), 32, "white"))
                yy += 64
            size = int(fit(lines, [(14, 140), (20, 116), (99, 96)]) * k)
            for l in lines:
                sh.append(dt(FONTS["hand"], l, size, "black@0.75", ypos=yy + 5))
                fr.append(dt(FONTS["hand"], l, size, "0xFFF6E5"))
                yy += int(size * 1.0)
        return sh, fr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--stil", choices=["magazin", "bold", "pov", "hand"], default="magazin")
    ap.add_argument("--uebergang", choices=["fade", "mix", "schnitt"], default="fade")
    ap.add_argument("--seed", type=int, default=0, help="Zufall fuer --uebergang mix")
    ap.add_argument("--hook", default="")
    ap.add_argument("--hook-klein", default="Insel Pag · Kroatien")
    ap.add_argument("--ende", default="")
    ap.add_argument("--ende-klein", default="traumurlaub-pag.com")
    ap.add_argument("--zeile", action="append", default=[], help='"VON-BIS:Text" Zwischentext')
    ap.add_argument("--text-sek", type=float, default=5.0, help="wie lange Hook/Ende sichtbar sind")
    ap.add_argument("--musik")
    a = ap.parse_args()
    st = Style(a.stil)

    with tempfile.TemporaryDirectory() as td:
        segs, total = [], 0.0
        for i, c in enumerate(a.clips):
            parts = c.split(":")
            src, start = parts[0], float(parts[1] or 0)
            dur = float(parts[2])
            focus = float(parts[3]) if len(parts) > 3 else 0.5
            p = f"{td}/s{i}.mp4"
            segment(src, start, dur, focus, p)
            segs.append((p, dur))
            total += dur

        # Clips verbinden
        fade = {"fade": 0.4, "mix": 0.5, "schnitt": 0.04}[a.uebergang]
        rng = random.Random(a.seed)
        inputs, chain, prev, offset = [], "", "0:v", 0.0
        for p, _ in segs:
            inputs += ["-i", p]
        for i in range(1, len(segs)):
            offset += segs[i - 1][1] - fade
            tr = rng.choice(MIX) if a.uebergang == "mix" else "fade"
            chain += f"[{prev}][{i}:v]xfade=transition={tr}:duration={fade}:offset={offset:.2f}[x{i}];"
            prev = f"x{i}"
        length = total - fade * (len(segs) - 1)

        # Texte: (klein, gross, von, bis, y, klein_schrift)
        texts = []
        if a.hook:
            texts.append((a.hook_klein, a.hook, 0.0, min(a.text_sek, length), st.y[0], False))
        for z in a.zeile:
            span, txt = z.split(":", 1)
            t0, t1 = (float(x) for x in span.split("-"))
            texts.append(("", txt, t0, min(t1, length), st.y[1], True))
        if a.ende:
            texts.append((a.ende_klein, a.ende, max(length - a.text_sek, 0), length, st.y[2], False))

        last = f"[{prev}]" if len(segs) > 1 else "[0:v]"
        shadow, front = [], []
        for tx in texts:
            s, f = st.layers(*tx[:5], small=tx[5])
            shadow += s; front += f
        if front:
            soft = ""
            if shadow:
                soft = (f"color=black@0.0:s={W}x{H}:r={FPS}:d={length:.2f},format=rgba,"
                        f"{','.join(shadow)},gblur=sigma=16[soft];")
                base = f"{last}[soft]overlay=format=auto,"
            else:
                base = f"{last}"
            fc = chain + soft + base + ",".join(front) + ",format=yuv420p[v]"
        else:
            fc = chain + f"{last}null,format=yuv420p[v]"

        cmd = ["ffmpeg", "-v", "error", "-y", *inputs]
        if a.musik:
            cmd += ["-i", str(ROOT / a.musik) if not Path(a.musik).is_absolute() else a.musik]
            afilter = ["-af", f"afade=t=out:st={max(length-1.5, 0):.2f}:d=1.5"]
        else:  # stille Tonspur - Instagram verarbeitet Videos ohne Audio manchmal nicht
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
            afilter = []
        cmd += ["-filter_complex", fc, "-map", "[v]", "-map", f"{len(segs)}:a", *afilter,
                "-c:a", "aac", "-b:a", "128k"]
        cmd += ["-t", f"{length:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                "-r", str(FPS), "-movflags", "+faststart", a.out]
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(cmd, check=True)
    print(f"Reel fertig: {a.out} ({length:.1f} s, Stil {a.stil}, Uebergang {a.uebergang})")


if __name__ == "__main__":
    main()
