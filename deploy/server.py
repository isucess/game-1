#!/usr/bin/env python3
"""Flying Numbers — tiny self-hosted server for the Mac mini.

Serves the game page and a shared leaderboard (scores.json next to this file).
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
GAME_HTML = os.path.join(HERE, "..", "index.html")
SCORES_FILE = os.environ.get("FN_SCORES_FILE", os.path.join(HERE, "scores.json"))
MAX_SCORES = 500
LOCK = threading.Lock()


def load_scores():
    try:
        with open(SCORES_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_scores(scores):
    tmp = SCORES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False)
    os.replace(tmp, SCORES_FILE)


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
    return {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "score": score,
        "turns": turns,
        "timeMs": time_ms,
        "range": 20,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def page_html():
    # The game file is written as artifact content (no <html>/<head> wrapper),
    # so wrap it in a proper document with the viewport the iPad needs.
    with open(GAME_HTML, encoding="utf-8") as f:
        body = f.read()
    head = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no\">"
        "<meta name=\"apple-mobile-web-app-capable\" content=\"yes\">"
        "<meta name=\"mobile-web-app-capable\" content=\"yes\">"
        "<meta name=\"apple-mobile-web-app-title\" content=\"Flying Numbers\">"
        "<meta name=\"apple-mobile-web-app-status-bar-style\" content=\"default\">"
        "<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
        "body{margin:0}</style></head><body>"
    )
    return (head + body + "</body></html>").encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "FlyingNumbers/1.0"

    def _send(self, code, payload, ctype="application/json; charset=utf-8"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, page_html(), "text/html; charset=utf-8")
        elif path == "/api/scores":
            with LOCK:
                self._send(200, load_scores())
        elif path == "/health":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/scores":
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
            scores = load_scores()
            scores.append(rec)
            scores.sort(key=lambda r: (-r["score"] / r.get("turns", 10), r["timeMs"]))
            save_scores(scores[:MAX_SCORES])
        self._send(201, rec)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("FN_PORT", "8090")))
    ap.add_argument("--host", default=os.environ.get("FN_HOST", "0.0.0.0"))
    args = ap.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Flying Numbers on http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
