#!/usr/bin/env python3
"""Website-Imagefilm "Yoga & Aktivwoche Pag" (16:9, 1920x1080).

Aufruf: python3 tools/imagefilm.py <medien-ordner> <song.mp3> <ausgabe.mp4> [--preview] [--stumm]
<medien-ordner> enthaelt die Originale aus Google Drive (Unterordner Apartments/ und Strand/).
Schnitt auf die Akzente der Musik, weiche Ueberblendungen, einheitliches Grading, dezente Typografie.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
F = ROOT / "tools/fonts"
W, H, FPS = 1920, 1080, 30
SONG_START = 90.08      # Einsatz der Phrase in "Flowing Piano" (Leberch, Pixabay)
LENGTH = 25.9           # bis zum natuerlichen Ausklingen des Songs
XF = 0.8                # Ueberblenddauer
CUTS = [5.15, 8.36, 10.33, 12.9, 15.47, 18.06, 20.37, 21.86]   # Akzente der Musik (s)
SHOTS = [  # (Clip im Repo-Katalog, Startzeit im Original, Grading-Zusatz)
    ("strand-036", 0.5, ""),                     # Szene 1: tuerkise Bucht mit Pag-Stadt (Drohne)
    ("strand-047", 1.5, ""),                     # Szene 2: Wanderer ueber der Bucht
    ("strand-016", 9.0, ""),                     #          Radfahrer auf dem Kuestenweg
    ("strand-018", 6.0, ""),                     #          Radfahrer entlang der Bucht
    ("strand-030", 0.2, ""),                     # Szene 3: Kopfstand am Meer
    ("strand-031", 0.3, ""),                     #          Akro-Yoga
    ("strand-050", 1.0, ""),                     # Szene 4: Treiben im tuerkisen Wasser
    ("strand-013", 1.0, ""),                     #          Strandbett
    ("strand-007", 0.5, ",eq=brightness=0.03:gamma=1.06"),  # Szene 5: Sonnenuntergang
]
GRADE = ("eq=contrast=1.04:saturation=1.06:gamma=0.99,"
         "colorbalance=rs=0.015:bs=-0.015:rh=0.025:bh=-0.02,unsharp=5:5:0.35")


def originals():
    m = {x["file"].split("/")[-1][:-4]: x for x in json.load(open(ROOT / "medien.json")) if x["type"] == "video"}
    return m


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def spaced(s):
    return " ".join(" " if c == " " else c for c in s.upper())


def alpha(t0, t1, fi=0.8, fo=0.8):
    return (f"if(lt(t,{t0}),0,if(lt(t,{t0+fi}),(t-{t0})/{fi},if(lt(t,{t1-fo}),1,"
            f"if(lt(t,{t1}),({t1}-t)/{fo},0))))")


def main():
    media, song, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    preview, stumm = "--preview" in sys.argv, "--stumm" in sys.argv
    cat = originals()
    bounds = [0.0] + CUTS + [LENGTH]
    inputs, chains = [], []
    for i, (key, start, extra) in enumerate(SHOTS):
        a, b = bounds[i], bounds[i + 1]
        dur = (b - a) + (XF / 2 if i > 0 else 0) + (XF / 2 if i < len(SHOTS) - 1 else 0)
        x = cat[key]
        src = media / ("Apartments" if x["ordner"] == "apartments" else "Strand") / x["original"]
        inputs += ["-ss", str(start), "-t", f"{dur + 0.1:.2f}", "-i", str(src)]
        chains.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
                      f"fps={FPS},setsar=1,{GRADE}{extra},trim=duration={dur:.3f},setpts=PTS-STARTPTS[c{i}]")
    # Ueberblendungen
    prev, fc = "c0", ";".join(chains) + ";"
    for i in range(1, len(SHOTS)):
        off = CUTS[i - 1] - XF / 2
        fc += f"[{prev}][c{i}]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{i}];"
        prev = f"x{i}"

    # Typografie (dezent): gesperrte Versalien (Montserrat) + kursive Serife (Playfair)
    T = [  # (font, text, size, y, t0, t1)
        ("Montserrat-SemiBold.ttf", spaced("Yoga & Aktivwoche"), 54, "h*0.24", 0.8, 4.8),
        ("PlayfairDisplay-MediumItalic.ttf", "Pag · Kroatien", 50, "h*0.24+86", 1.4, 4.8),
        ("PlayfairDisplay-MediumItalic.ttf", "Finde deine Balance.", 66, "h*0.16", 13.5, 17.7),
        ("PlayfairDisplay-MediumItalic.ttf", "Bewegung. Natur. Entspannung.", 62, "h*0.26", 22.2, LENGTH),
        ("Montserrat-SemiBold.ttf", spaced("traumurlaub-pag.com"), 34, "h*0.26+100", 23.0, LENGTH),
    ]
    def dt(font, text, size, y, t0, t1, color, dy=0):
        return (f"drawtext=fontfile={F / font}:text='{esc(text)}':fontsize={size}:fontcolor={color}"
                f":x=(w-tw)/2:y={y}+{dy}:alpha='{alpha(t0, t1)}'")
    shadow = ",".join(dt(*t, color="black@0.55", dy=3) for t in T)
    front = ",".join(dt(*t, color="white@0.97") for t in T)
    fc += (f"color=black@0:s={W}x{H}:r={FPS}:d={LENGTH},format=rgba,{shadow},gblur=sigma=14[sh];"
           f"[{prev}][sh]overlay=format=auto,{front},"
           f"fade=t=in:st=0:d=0.6,fade=t=out:st={LENGTH-0.8}:d=0.8,format=yuv420p[v]")

    cmd = ["ffmpeg", "-v", "error", "-y", *inputs]
    maps = ["-map", "[v]"]
    if not stumm:
        cmd += ["-ss", str(SONG_START), "-t", str(LENGTH), "-i", song]
        fc += (f";[{len(SHOTS)}:a]afade=t=in:st=0:d=0.3,afade=t=out:st={LENGTH-2.5}:d=2.5,"
               f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]")
        maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    if preview:
        venc = ["-vf", "scale=1280:720", "-c:v", "libx264", "-preset", "medium", "-crf", "24"]
        cmd += ["-filter_complex", fc + ";[v]scale=1280:720[vp]"]
        maps[1] = "[vp]"
        venc = ["-c:v", "libx264", "-preset", "medium", "-crf", "24"]
    else:
        cmd += ["-filter_complex", fc]
        venc = ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-level", "4.1"]
    cmd += maps + venc + ["-pix_fmt", "yuv420p", "-r", str(FPS), "-t", str(LENGTH), "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print("fertig:", out)


if __name__ == "__main__":
    main()
