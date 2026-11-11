#!/usr/bin/env python3
"""Schneidet aus mehreren Clips ein Reel (1080x1920, 30 fps, H.264).

Aufruf:
  python3 tools/make_reel.py reels/2026-11-12.mp4 \
      --hook "Nur ein paar Schritte|bis hierher" --ende "Sommer 2027|jetzt anfragen" --musik musik/sommer-1.m4a \
      videos/strand-003.mp4:2:3.5 videos/apartments-002.mp4:0:3 fotos/strand-010.jpg::3

Jeder Clip ist  DATEI:START:DAUER  (Sekunden). Fotos bekommen einen langsamen Zoom.
Querformat wird mittig auf 9:16 zugeschnitten. Optional --focus 0.0-1.0 je Clip
als 4. Feld (horizontale Position des Ausschnitts, 0.5 = Mitte).
Ton: standardmaessig stumm (Wind/Gespraeche); --musik DATEI legt eine Tonspur
darunter (nur lizenzfreie Musik!).
"""
import argparse, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "tools/fonts/Inter-ExtraBold.otf"
FONT_GROSS = ROOT / "tools/fonts/PlayfairDisplay-MediumItalic.ttf"  # nur Latin-1 (keine ć/č/š!)
FONT_KLEIN = ROOT / "tools/fonts/Montserrat-SemiBold.ttf"
W, H, FPS = 1080, 1920, 30


def esc(t):
    # Emojis kann die Schrift nicht darstellen -> entfernen
    t = "".join(ch for ch in t if ord(ch) < 0x2190 or 0x2190 <= ord(ch) < 0x2300 and ch in "→←").strip()
    t = " ".join(t.split(" "))  # nur normale Leerzeichen zusammenfassen (Sperrsatz-Abstaende bleiben)
    t = " ".join(p for p in t.split(" ") if p)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--hook", default="")
    ap.add_argument("--hook-klein", default="Insel Pag · Kroatien")
    ap.add_argument("--ende", default="")
    ap.add_argument("--ende-klein", default="traumurlaub-pag.com")
    ap.add_argument("--text-sek", type=float, default=5.0, help="wie lange jeder Text sichtbar ist")
    ap.add_argument("--musik")
    a = ap.parse_args()

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

        # Clips mit kurzen Ueberblendungen verbinden
        fade = 0.4
        inputs, chain, prev, offset = [], "", "0:v", 0.0
        for i, (p, d) in enumerate(segs):
            inputs += ["-i", p]
        for i in range(1, len(segs)):
            offset += segs[i - 1][1] - fade
            chain += f"[{prev}][{i}:v]xfade=transition=fade:duration={fade}:offset={offset:.2f}[x{i}];"
            prev = f"x{i}"
        length = total - fade * (len(segs) - 1)

        # Texte im Magazin-Stil: kleine, gesperrte Zeile in Grossbuchstaben (Montserrat) ueber einer
        # grossen, kursiven Serifenzeile (Playfair Display). Weicher Schatten, sanftes Einblenden
        # mit leichtem Hochgleiten.
        texts = []
        if a.hook:
            texts.append((a.hook_klein, a.hook, 0.3, min(0.3 + a.text_sek, length), 330))
        if a.ende:
            texts.append((a.ende_klein, a.ende, max(length - a.text_sek, 0), length, 1180))

        def alpha(t0, t1, f=0.6):
            return (f"if(lt(t,{t0:.2f}),0,if(lt(t,{t0+f:.2f}),(t-{t0:.2f})/{f},"
                    f"if(lt(t,{t1-f:.2f}),1,if(lt(t,{t1:.2f}),({t1:.2f}-t)/{f},0))))")

        def spaced(s):  # Sperrsatz fuer die kleine Zeile
            return " ".join(" " if c == " " else c for c in s.upper())  # Halbgeviert als Wortabstand

        def draw(klein, gross, t0, t1, y, color, dy=0):
            lift = f"18*max(0\\,1-(t-{t0:.2f})/0.7)"  # gleitet beim Einblenden 18 px nach oben
            al = alpha(t0, t1)
            out, yy = [], y + dy
            if klein:
                out.append(f"drawtext=fontfile={FONT_KLEIN}:text='{esc(spaced(klein))}':fontsize=34"
                           f":fontcolor={color}:x=(w-tw)/2:y={yy}+{lift}:alpha='{al}'")
                yy += 70
            lines = [l.strip() for l in gross.split("|")]
            size = 104 if max(len(l) for l in lines) <= 16 else 88 if max(len(l) for l in lines) <= 20 else 74
            for l in lines:
                out.append(f"drawtext=fontfile={FONT_GROSS}:text='{esc(l)}':fontsize={size}"
                           f":fontcolor={color}:x=(w-tw)/2:y={yy}+{lift}:alpha='{al}'")
                yy += int(size * 1.18)
            return ",".join(out)

        last = f"[{prev}]" if len(segs) > 1 else "[0:v]"
        if texts:
            shadow = ",".join(draw(*tx, color="black@0.7", dy=4) for tx in texts)
            front = ",".join(draw(*tx, color="white") for tx in texts)
            fc = (chain + f"color=black@0.0:s={W}x{H}:r={FPS}:d={length:.2f},format=rgba,"
                  f"{shadow},gblur=sigma=16[soft];"
                  f"{last}[soft]overlay=format=auto,{front},format=yuv420p[v]")
        else:
            fc = chain + f"{last}null,format=yuv420p[v]"

        cmd = ["ffmpeg", "-v", "error", "-y", *inputs]
        if a.musik:
            cmd += ["-i", a.musik]
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
    print(f"Reel fertig: {a.out} ({length:.1f} s)")


if __name__ == "__main__":
    main()
