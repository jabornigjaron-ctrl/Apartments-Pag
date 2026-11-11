#!/usr/bin/env python3
"""Veroeffentlicht einen freigegebenen Post auf Instagram (traumurlaub_pag).

Aufruf:  python3 tools/publish.py posts/2026-11-12.json [--dry-run]

Die Post-Datei (JSON) enthaelt:
  {"typ": "foto" | "karussell" | "reel",
   "medien": ["fotos/strand-001.jpg", ...]   # Pfade im Repo, muessen gepusht sein
   "caption": "...",
   "status": "freigegeben"}                  # nur dann wird gepostet

Der Token wird vom Netzwerk-Proxy der Cloud-Umgebung automatisch als
Authorization-Header an graph.facebook.com angehaengt; das Skript kennt ihn nicht.
"""
import json, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

IG_ID = "17841438885941125"
API = "https://graph.facebook.com/v23.0"
RAW = "https://raw.githubusercontent.com/jabornigjaron-ctrl/apartments-pag/main/"


def call(method, path, **params):
    url = f"{API}/{path}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API-Fehler {e.code} bei {path}: {e.read().decode()}")


def check_url(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        if r.status != 200:
            raise SystemExit(f"Medium nicht oeffentlich erreichbar: {url}")


def wait_ready(cid, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = call("GET", cid, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise SystemExit(f"Container {cid} fehlgeschlagen: {st}")
        time.sleep(10)
    raise SystemExit(f"Container {cid} nach {timeout}s nicht fertig")


def container(media, kind, caption=None, child=False):
    url = RAW + urllib.parse.quote(media)
    check_url(url)
    p = {}
    if kind == "video":
        p["media_type"] = "VIDEO" if child else "REELS"
        p["video_url"] = url
        if not child:
            p["share_to_feed"] = "true"
    else:
        p["image_url"] = url
    if child:
        p["is_carousel_item"] = "true"
    if caption is not None:
        p["caption"] = caption
    return call("POST", f"{IG_ID}/media", **p)["id"]


def kind_of(path):
    return "video" if path.lower().endswith((".mp4", ".mov")) else "image"


def main():
    post_file = Path(sys.argv[1])
    dry = "--dry-run" in sys.argv
    post = json.loads(post_file.read_text())
    if post.get("status") != "freigegeben":
        raise SystemExit(f"Status ist '{post.get('status')}', nicht 'freigegeben' - es wird nichts gepostet.")
    medien, cap, typ = post["medien"], post["caption"], post["typ"]
    if dry:
        for m in medien:
            check_url(RAW + urllib.parse.quote(m))
        print("Dry-Run ok:", typ, medien)
        return

    if typ == "karussell":
        kids = [container(m, kind_of(m), child=True) for m in medien]
        for k in kids:
            wait_ready(k)
        cid = call("POST", f"{IG_ID}/media", media_type="CAROUSEL", children=",".join(kids), caption=cap)["id"]
    else:
        cid = container(medien[0], kind_of(medien[0]), caption=cap)
    wait_ready(cid)
    res = call("POST", f"{IG_ID}/media_publish", creation_id=cid)
    info = call("GET", res["id"], fields="permalink,timestamp")
    post["status"] = "gepostet"
    post["media_id"] = res["id"]
    post["permalink"] = info.get("permalink")
    post["gepostet_am"] = datetime.now(timezone.utc).isoformat()
    post_file.write_text(json.dumps(post, indent=1, ensure_ascii=False))
    print("Gepostet:", info.get("permalink"))


if __name__ == "__main__":
    main()
