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

0. **Start einer frischen Sitzung:** Ist das Repo nicht da, mit `add_repo` (jabornigjaron-ctrl/apartments-pag,
   access push) holen und klonen. `git pull`. Existiert `posts/<heute>.json` schon mit Status
   `freigegeben` oder `gepostet` – **oder ist ein anderer Post mit `"geplant_fuer": "<heute>"` eingeplant**
   (nachgeholte Posts) –, keinen neuen Entwurf machen, nur kurz Bescheid geben. Posts mit `geplant_fuer`
   werden an jenem Tag um 18:00 gepostet (send_later ist bereits geplant).
1. **Entwurf (jeden Morgen, Vorschau bis 7:00):**
   - `kunde.md`, `videos.md`, `medien.json` und die letzten ~14 Dateien in `posts/` lesen.
   - **Jeden Tag ein Reel** (Wunsch des Betreuers). Themen abwechseln: Meer/Türkis, Apartments,
     Sonnenuntergang, Aktiv (Wandern/Rad), Strandbar/Beach-Club, Zrće/Party (Freunde/Maturareise), Familie.
   - Clips möglichst nicht aus den letzten 7 Tagen; gleicher Clip nur mit anderem Ausschnitt/Startzeit.
     Vorher Einzelbilder ansehen (`ffmpeg -ss T -i video -frames:v 1`), damit Ausschnitt und Motiv passen;
     Text darf kein wichtiges Motiv (Gesicht, Person) verdecken.
   - Reel mit `tools/make_reel.py` → `reels/JJJJ-MM-TT.mp4` (8–20 s). Texte ohne Emojis, „|“ = Zeilenumbruch,
     max. ~16–20 Zeichen pro Zeile, keine ć/č/š/ž im Videotext („Zrce“ schreiben). Hook steht ab Bild 1.
   - **Abwechslung (Wunsch des Betreuers – nicht zweimal hintereinander gleich!):** Stil (`--stil magazin|bold|pov|hand`,
     Übersicht `stile.jpg`), Übergang (`--uebergang fade|mix|schnitt`, bei mix `--seed` variieren) und Musik
     (`musik/`: sommer-1..3 chill, house-1..2 tanzbar, lofi-1..2 entspannt, cinematic-1..2 ruhig) rotieren;
     in `posts/*.json` unter `"design"` festhalten. Passende Kombis: bold+schnitt+house (schnell, Liste),
     pov+mix+lofi (POV-Story), magazin+fade+sommer/cinematic (edel), hand+fade+lofi/cinematic (Sonnenuntergang).
     Bei house im Takt schneiden: 122 bpm → 4 Schläge = 1,967 s (+0,04 bei schnitt). Neue Musik:
     `tools/music.py --stil chill|house|lofi|cinematic --seed N --key K`, danach mit ffmpeg `loudnorm=I=-16` nach m4a.
   - **Reichweite (viral):** In den ersten 1–2 s ein starker Hook (POV, Frage, Zahl, „Speicher dir das“,
     „Das hier ist kein Filter“); 10–16 s, damit es loopt; Formate wechseln: Listen „3 Gründe…“ (`--zeile
     "VON-BIS:Text"`), POV, Vorher/Nachher (Alltag→Pag), „Rate wo das ist“, Sonnenuntergang-Mood.
     Ende mit Frage oder Aufforderung (Kommentieren, Markieren, Speichern, Teilen). Caption: erste Zeile = Hook,
     Frage für Kommentare, 3–6 passende Hashtags. Keine Versprechen, dass es viral geht.
     Karussell: 3–8 Fotos, erstes Bild das stärkste.
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
