#!/usr/bin/env bash
# Flying Numbers — auto deploy on the Mac mini. launchd runs this every minute: when GitHub `main` has a new
# commit it moves this checkout to it, restarts the server if server.py changed (index.html is read on every
# request, so a page-only change needs no restart) and checks the server still answers. A commit that breaks
# the server is rolled back and not retried; pushing a fix to `main` makes it try again.
#
#   bash deploy/autodeploy.sh --install     # install the launchd job (once, after install-macmini.sh)
#   bash deploy/autodeploy.sh               # run one check by hand
#
# Log: ~/Library/Logs/flying-numbers/autodeploy.log (one line per deploy; quiet when nothing changed).
# Uninstall:
#   launchctl bootout gui/$(id -u)/com.flyingnumbers.autodeploy
#   rm ~/Library/LaunchAgents/com.flyingnumbers.autodeploy.plist
set -uo pipefail
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export GIT_TERMINAL_PROMPT=0

LABEL="com.flyingnumbers.autodeploy"
SERVER_LABEL="com.flyingnumbers.server"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
SERVER_PLIST="$HOME/Library/LaunchAgents/$SERVER_LABEL.plist"
LOG_DIR="$HOME/Library/Logs/flying-numbers"
LOG="$LOG_DIR/autodeploy.log"
FAILED_SHA="$LOG_DIR/autodeploy_failed_sha"
LOCK="$LOG_DIR/autodeploy.lock"
CHECK_INTERVAL_SECONDS=60
STALE_LOCK_MINUTES=10   # a run killed mid-way (reboot, crash) must not block auto deploy forever
HEALTH_TRIES=15

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >>"$LOG"; }

server_port() { /usr/libexec/PlistBuddy -c "Print :ProgramArguments:3" "$SERVER_PLIST" 2>/dev/null; }

healthy() {
  local port
  port="$(server_port)" || return 1
  for _ in $(seq 1 "$HEALTH_TRIES"); do
    if curl -fsS "http://127.0.0.1:$port/health" >/dev/null 2>&1 \
      && curl -fsS -o /dev/null "http://127.0.0.1:$port/" 2>/dev/null; then
      return 0
    fi
    sleep 1
  done
  return 1
}

restart_server() { launchctl kickstart -k "gui/$(id -u)/$SERVER_LABEL"; }

install() {
  [ -f "$SERVER_PLIST" ] || { echo "Server not installed yet. Run: bash deploy/install-macmini.sh"; exit 1; }
  mkdir -p "$LOG_DIR"
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$DIR/deploy/autodeploy.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>StartInterval</key><integer>$CHECK_INTERVAL_SECONDS</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$LOG_DIR/autodeploy.out.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/autodeploy.out.log</string>
</dict>
</plist>
EOF
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  launchctl enable "gui/$(id -u)/$LABEL"
  echo "✅ Auto deploy installed: checks GitHub main every ${CHECK_INTERVAL_SECONDS}s"
  echo "   Log: $LOG"
}

deploy() {
  cd "$DIR" || { log "missing checkout $DIR"; return 1; }
  git fetch -q origin main || { log "git fetch failed"; return 1; }
  local old new
  old="$(git rev-parse HEAD)"
  new="$(git rev-parse origin/main)"
  [ "$new" = "$old" ] && return 0
  [ "$new" = "$(cat "$FAILED_SHA" 2>/dev/null)" ] && return 0   # already tried and failed: wait for a fix

  log "new main ${new:0:7}: $(git log -1 --format=%s "$new")"
  local server_changed=0
  git diff --quiet "$old" "$new" -- deploy/server.py || server_changed=1
  git reset -q --hard "$new"   # scores.json is git-ignored, so the leaderboard survives
  [ "$server_changed" = 1 ] && restart_server

  if healthy; then
    rm -f "$FAILED_SHA"
    log "deployed ${new:0:7} OK$([ "$server_changed" = 1 ] && echo ' (server restarted)')"
    return 0
  fi

  echo "$new" >"$FAILED_SHA"
  log "server unhealthy on ${new:0:7}, rolling back to ${old:0:7}"
  git reset -q --hard "$old"
  restart_server
  if healthy; then log "rolled back to ${old:0:7} OK"; else log "rollback still unhealthy: check $LOG_DIR/server.log"; fi
  return 1
}

main() {
  mkdir -p "$LOG_DIR"
  if [ "${1:-}" = "--install" ]; then install; return; fi
  [ -d "$LOCK" ] && [ -n "$(find "$LOCK" -maxdepth 0 -mmin +$STALE_LOCK_MINUTES)" ] && rmdir "$LOCK"
  mkdir "$LOCK" 2>/dev/null || return 0   # another run is still in progress
  trap 'rmdir "$LOCK"' EXIT
  deploy
}

# Everything runs inside main(), which bash reads in full before running it, so `git reset` replacing this
# very file mid-run cannot make bash execute half of an old and half of a new script.
main "$@"
exit $?
