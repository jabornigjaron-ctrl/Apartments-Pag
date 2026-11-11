# Pag Instagram Agent

Dieses Repo betreibt den täglichen Instagram-Post für **@traumurlaub_pag** (Apartments in Gajac, Insel Pag).
Sprich mit dem Betreuer **Deutsch**, kurz und einfach (kein Fachjargon).

- `kunde.md` – Angebot, Zielgruppen, Stil, Regeln. **Vor jedem Post lesen.**
- `medien.json` – alle Fotos/Videos (Typ, Größe, Ordner `apartments`/`strand`, Dauer)
- `fotos/`, `videos/` – aufbereitete Medien (GPS entfernt, Instagram-Größe)
- `reels/` – fertig geschnittene Reels · `posts/` – ein JSON pro Tag (Entwurf → freigegeben → gepostet)
- `tools/make_reel.py` – schneidet Reels (9:16, Überblendungen, Text) · `tools/publish.py` – postet über die Graph API
- `.claude/skills/ig-*` – Text-Skills (ig-caption, ig-reel, ig-human, ig-carousel …)

Der Instagram-Token liegt NICHT im Repo: der Netzwerk-Proxy der Cloud-Umgebung hängt ihn an
Anfragen an graph.facebook.com an. Niemals einen Token ins Repo, in Logs oder in den Chat schreiben.

## Täglicher Ablauf (Freigabe-Pflicht!)

1. **Entwurf (morgens):**
   - `kunde.md`, `medien.json` und die letzten ~14 Dateien in `posts/` lesen.
   - Format im Wechsel: Reel → Karussell → Reel → Foto → … (Reels bevorzugt, ca. 4 von 7 Tagen).
   - Medien wählen, die in den letzten 30 Tagen nicht verwendet wurden. Vorher Einzelbilder
     ansehen (`ffmpeg -ss T -i video -frames:v 1`), damit Ausschnitt und Motiv passen.
   - Reel: 3–6 Clips à 2–4 s mit `tools/make_reel.py` → `reels/JJJJ-MM-TT.mp4` (8–20 s). Texte im Magazin-Stil
     (kleine gesperrte Zeile `--hook-klein`/`--ende-klein` + große kursive Serifenzeile, weicher Schatten,
     kein Kasten), ohne Emojis, „|“ = Zeilenumbruch, max. ~16–20 Zeichen pro Zeile, keine ć/č/š/ž im
     Videotext (Schrift kann sie nicht – „Zrce“ schreiben); Ende z. B. „Sommer 2027|jetzt anfragen“. Jeder Text ~5 s sichtbar (Standard `--text-sek 5`), letzter Clip ≥ 5 s. Immer `--musik musik/sommer-N.m4a` (im Wechsel).
     Die Musik ist selbst erzeugt (`tools/music.py`, lizenzfrei); neue Stücke mit anderem --seed/--key/--bpm. Karussell: 3–8 Fotos, erstes Bild das stärkste.
     Foto/Karussell-Seitenverhältnis muss zwischen 4:5 und 1.91:1 liegen – sonst vorher auf 4:5 (1080×1350) zuschneiden.
   - Caption mit den Skills ig-caption + ig-human: Stil aus `kunde.md`, eine klare Aufforderung,
     3–6 Hashtags. Nichts erfinden (Preise, Termine, Ausstattung).
   - `posts/JJJJ-MM-TT.json` mit `{"typ","medien","caption","status":"entwurf"}` anlegen,
     committen und auf `main` pushen (Medien müssen öffentlich auf GitHub liegen).
   - Dem Betreuer Vorschau schicken (SendUserFile: Reel bzw. Bilder, status proactive) + Caption als Text,
     und fragen: „Passt das? Antworte mit **ok** oder sag, was ich ändern soll.“
2. **Änderungswünsche:** umsetzen, neu zeigen, erneut fragen.
3. **Bei „ok“:** Status auf `freigegeben`, committen + pushen, `python3 tools/publish.py posts/… --dry-run`
   prüfen, dann mit `send_later` eine Nachricht für **18:00 Europe/Vienna** an diese Sitzung planen
   („Jetzt den freigegebenen Post veröffentlichen“). Ist es schon nach 18:00, sofort posten.
4. **Um 18:00:** `python3 tools/publish.py posts/JJJJ-MM-TT.json`, Ergebnis committen + pushen,
   dem Betreuer den Link zum Post schicken.
5. Ohne „ok“ wird **nie** gepostet. Kein Freigabe bis 23:00 → Tag auslassen, Entwurf bleibt liegen.

## Sonstiges
- Tageslimit Instagram: 100 Posts / 24 h (wir brauchen 1).
- Fehler 190 (Token ungültig/abgelaufen): Betreuer bitten, in der Meta-App unter
  „API setup with Unified login → Zugriffstokens generieren“ einen neuen Token zu erzeugen; über
  request_credential für graph.facebook.com speichern lassen.
- Neue Fotos/Videos: Betreuer lädt sie in den geteilten Google-Drive-Ordner; mit `drive.usercontent.google.com/download?id=…&export=download&confirm=t`
  laden und genauso aufbereiten (Fotos max. 1440 px, ohne EXIF; Videos 1080p H.264 CRF 23, faststart).
