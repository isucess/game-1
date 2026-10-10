#!/usr/bin/env python3
"""Kids games — tiny self-hosted server for the Mac mini.

    /                         game menu (index.html)
    /flying-numbers/          Flying Numbers
    /khung-long-danh-van/     Khủng long đánh vần
    /<game>/api/scores        that game's shared leaderboard (GET list, POST one score)

Standard library only, so it runs on the stock macOS python3.

    python3 server.py --port 8090
"""
import argparse
import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCORES_DIR = os.environ.get("FN_SCORES_DIR", HERE)

# slug -> (page language, leaderboard file). Flying Numbers keeps its original scores.json.
GAMES = {
    "flying-numbers": ("en", "scores.json"),
    "khung-long-danh-van": ("vi", "scores-khung-long-danh-van.json"),
}
MAX_SCORES = 500
LOCK = threading.Lock()


def scores_path(slug):
    return os.path.join(SCORES_DIR, GAMES[slug][1])


def load_scores(slug):
    try:
        with open(scores_path(slug), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_scores(slug, scores):
    path = scores_path(slug)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False)
    os.replace(tmp, path)


def clean_record(body):
    """Validate a posted score; return a stored record or None."""
    try:
        name = str(body.get("name", "")).strip()[:16]
        turns = int(body.get("turns", 10))
        score = int(body.get("score"))
        time_ms = int(body.get("timeMs"))
    except (TypeError, ValueError):
        return None
    if not name or turns not in (5, 10) or not 0 <= score <= turns or not 0 < time_ms < 6 * 3600 * 1000:
        return None
    rec = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "score": score,
        "turns": turns,
        "timeMs": time_ms,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if isinstance(body.get("set"), str):
        rec["set"] = body["set"].strip()[:40]
    if isinstance(body.get("range"), int):
        rec["range"] = body["range"]
    return rec


def page_html(rel_path, lang):
    # Pages are written as artifact content (no <html>/<head> wrapper), so wrap them in a proper
    # document with the viewport the iPad needs.
    with open(os.path.join(ROOT, rel_path), encoding="utf-8") as f:
        body = f.read()
    head = (
        f"<!doctype html><html lang=\"{lang}\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no\">"
        "<meta name=\"apple-mobile-web-app-capable\" content=\"yes\">"
        "<meta name=\"mobile-web-app-capable\" content=\"yes\">"
        "<meta name=\"apple-mobile-web-app-title\" content=\"Will &amp; Kem\">"
        "<meta name=\"apple-mobile-web-app-status-bar-style\" content=\"default\">"
        "<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
        "body{margin:0}</style></head><body>"
    )
    return (head + body + "</body></html>").encode("utf-8")


def route(path):
    """Return (kind, slug) for a request path: kind is page | api | redirect | health | None."""
    path = path.split("?", 1)[0]
    if path in ("/", "/index.html"):
        return "page", None
    if path == "/health":
        return "health", None
    if path == "/api/scores":                      # old Flying Numbers URL
        return "api", "flying-numbers"
    parts = [p for p in path.split("/") if p]
    if parts and parts[0] in GAMES:
        slug = parts[0]
        rest = parts[1:]
        if not rest:
            return ("page", slug) if path.endswith("/") else ("redirect", slug)
        if rest == ["index.html"]:
            return "page", slug
        if rest == ["api", "scores"]:
            return "api", slug
    return None, None


class Handler(BaseHTTPRequestHandler):
    server_version = "KidsGames/2.0"

    def _send(self, code, payload, ctype="application/json; charset=utf-8", headers=None):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        kind, slug = route(self.path)
        if kind == "page":
            if slug is None:
                self._send(200, page_html("index.html", "vi"), "text/html; charset=utf-8")
            else:
                self._send(200, page_html(f"{slug}/index.html", GAMES[slug][0]), "text/html; charset=utf-8")
        elif kind == "redirect":
            self._send(301, b"", "text/plain", {"Location": f"/{slug}/"})
        elif kind == "api":
            with LOCK:
                self._send(200, load_scores(slug))
        elif kind == "health":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        kind, slug = route(self.path)
        if kind != "api":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= 2048:
            return self._send(400, {"error": "bad body"})
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        rec = clean_record(body if isinstance(body, dict) else {})
        if not rec:
            return self._send(400, {"error": "bad score"})
        with LOCK:
            scores = load_scores(slug)
            scores.append(rec)
            scores.sort(key=lambda r: (-r["score"] / r.get("turns", 10), r["timeMs"]))
            save_scores(slug, scores[:MAX_SCORES])
        self._send(201, rec)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("FN_PORT", "8090")))
    ap.add_argument("--host", default=os.environ.get("FN_HOST", "0.0.0.0"))
    args = ap.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Kids games on http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
