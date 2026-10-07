#!/usr/bin/env bash
# Flying Numbers — install as an always-on launchd service on the Mac mini.
#
#   bash deploy/install-macmini.sh          # auto-pick a free port from 8090
#   bash deploy/install-macmini.sh 8095     # or start the search from 8095
#
# Re-running is safe: it reloads the service and keeps the same port if it is
# still ours. Uninstall:
#   launchctl bootout gui/$(id -u)/com.flyingnumbers.server
#   rm ~/Library/LaunchAgents/com.flyingnumbers.server.plist
set -euo pipefail

LABEL="com.flyingnumbers.server"
DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/flying-numbers"
PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "python3 not found. Install Xcode Command Line Tools: xcode-select --install"; exit 1; }

# Ports already used by other services on this Mac mini (pod web/bot, listing tool, mini-helper, vite).
RESERVED="5173 5174 8080 8081 8082 8084 9000 9001 9002 9003 9010 9100"

in_use() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

# Stop an existing copy first so its own port counts as free.
if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  sleep 1
fi

PORT="${1:-8090}"
while in_use "$PORT" || [[ " $RESERVED " == *" $PORT "* ]]; do
  PORT=$((PORT + 1))
  [ "$PORT" -lt 8200 ] || { echo "No free port found between ${1:-8090} and 8199"; exit 1; }
done

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$DIR/server.py</string>
    <string>--port</string>
    <string>$PORT</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG_DIR/server.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/server.log</string>
</dict>
</plist>
EOF

launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/$LABEL"

for _ in 1 2 3 4 5 6 7 8 9 10; do
  curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break
  sleep 0.5
done

if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo '<mac-mini-ip>')"
  echo ""
  echo "✅ Flying Numbers is running on port $PORT"
  echo "   On this Mac:       http://localhost:$PORT"
  echo "   iPad on same WiFi: http://$IP:$PORT"
  echo "   Logs:              $LOG_DIR/server.log"
  echo "   Scores file:       $DIR/scores.json"
else
  echo "❌ Service did not start. Check $LOG_DIR/server.log"
  exit 1
fi
