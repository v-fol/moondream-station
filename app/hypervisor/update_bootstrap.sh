#!/usr/bin/env bash
#
# Usage:
#   update_bootstrap.sh <NEW_EXE_PATH> <OLD_EXE_PATH> <PARENT_PID> <SLEEP_TIME> <PLATFORM>
#
# PLATFORM must be either:  mac   |   ubuntu
#
# Replaces the running bundle/executable with an updated one and launches it.

set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 NEW_EXE_PATH OLD_EXE_PATH PARENT_PID SLEEP_TIME PLATFORM"
  exit 2
fi

NEW_EXE_PATH="$1"
OLD_EXE_PATH="$2"
PARENT_PID="$3"
SLEEP_TIME="$4"
PLATFORM="$5"

echo "[update_bootstrap.sh] --------------------------------------------------"
echo "[update_bootstrap.sh]   NEW_EXE_PATH:  $NEW_EXE_PATH"
echo "[update_bootstrap.sh]   OLD_EXE_PATH:  $OLD_EXE_PATH"
echo "[update_bootstrap.sh]   PARENT_PID:    $PARENT_PID"
echo "[update_bootstrap.sh]   SLEEP_TIME:    $SLEEP_TIME"
echo "[update_bootstrap.sh]   PLATFORM:      $PLATFORM"

# ──────────────────────────────────────────────────────────────────────────────
# 1) Kill the parent if it's still running
if kill -0 "$PARENT_PID" 2>/dev/null; then
  echo "[update_bootstrap.sh] Parent ($PARENT_PID) is still alive; killing…"
  kill "$PARENT_PID" 2>/dev/null || true
  sleep 1
  if kill -0 "$PARENT_PID" 2>/dev/null; then
    echo "[update_bootstrap.sh] Parent still alive, sending SIGKILL…"
    kill -9 "$PARENT_PID" 2>/dev/null || true
  fi
else
  echo "[update_bootstrap.sh] Parent ($PARENT_PID) not running or already exited."
fi

# ──────────────────────────────────────────────────────────────────────────────
# 2) Sleep a bit
echo "[update_bootstrap.sh] Sleeping for $SLEEP_TIME seconds…"
sleep "$SLEEP_TIME"

# ──────────────────────────────────────────────────────────────────────────────
# 3) Replace old target with new target
echo "[update_bootstrap.sh] Replacing old target…"
rm -rf "$OLD_EXE_PATH"
mv "$NEW_EXE_PATH" "$OLD_EXE_PATH"

if { [ "$PLATFORM" = "mac" ] && [ -d "$OLD_EXE_PATH" ]; } ||
   { [ "$PLATFORM" = "ubuntu" ] && [ -f "$OLD_EXE_PATH" ]; }; then
  echo "[update_bootstrap.sh] New target successfully installed."
else
  echo "[update_bootstrap.sh] ERROR: Target not found at $OLD_EXE_PATH."
  exit 1
fi

chmod +x "$OLD_EXE_PATH" || true

# ──────────────────────────────────────────────────────────────────────────────
# 4) Launch the updated app
echo "[update_bootstrap.sh] Launching updated app…"

if [ "$PLATFORM" = "mac" ]; then
  # Open the .app bundle in a new macOS Terminal window
  osascript <<EOF
tell application "Terminal"
    activate
    do script "open \"${OLD_EXE_PATH}\""
end tell
EOF

elif [ "$PLATFORM" = "ubuntu" ]; then
  if ! command -v gnome-terminal >/dev/null 2>&1; then
    echo "[update_bootstrap.sh] ERROR: gnome-terminal not found."
    exit 2
  fi

  gnome-terminal -- bash -c "\"$OLD_EXE_PATH\" ; exec bash"

else
  echo "[update_bootstrap.sh] ERROR: Unknown platform '$PLATFORM'."
  exit 2
fi

echo "[update_bootstrap.sh] Done. Exiting script."
exit 0