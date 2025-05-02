#!/usr/bin/env bash
#
# Usage:
#   update_bootstrap.sh <NEW_EXE_PATH> <OLD_EXE_PATH> <PARENT_PID> <SLEEP_TIME>

NEW_EXE_PATH="$1"
OLD_EXE_PATH="$2"
PARENT_PID="$3"
SLEEP_TIME="$4"

echo "[update_bootstrap.sh] --------------------------------------------------"
echo "[update_bootstrap.sh]   NEW_EXE_PATH:  $NEW_EXE_PATH"
echo "[update_bootstrap.sh]   OLD_EXE_PATH:  $OLD_EXE_PATH"
echo "[update_bootstrap.sh]   PARENT_PID:    $PARENT_PID"
echo "[update_bootstrap.sh]   SLEEP_TIME:    $SLEEP_TIME"

# 1) Kill the parent if it's still running
if kill -0 "$PARENT_PID" 2>/dev/null; then
  echo "[update_bootstrap.sh] Parent ($PARENT_PID) is still alive; killing..."
  kill "$PARENT_PID" 2>/dev/null
  sleep 1
  if kill -0 "$PARENT_PID" 2>/dev/null; then
    echo "[update_bootstrap.sh] Parent still alive, sending SIGKILL..."
    kill -9 "$PARENT_PID" 2>/dev/null
  fi
else
  echo "[update_bootstrap.sh] Parent ($PARENT_PID) not running or already exited."
fi

# 2) Sleep a bit
echo "[update_bootstrap.sh] Sleeping for $SLEEP_TIME seconds..."
sleep "$SLEEP_TIME"

# 3) Remove old app and replace it with the new one.
echo "[update_bootstrap.sh] Overwriting old bootstrap with the new one..."
rm -rf "$OLD_EXE_PATH"
mv "$NEW_EXE_PATH" "$OLD_EXE_PATH"

if [ ! -d "$OLD_EXE_PATH" ]; then
  echo "[update_bootstrap.sh] ERROR: The new bundle was not placed at $OLD_EXE_PATH."
  exit 1
fi

chmod +x "$OLD_EXE_PATH"
echo "[update_bootstrap.sh] New executable set at $OLD_EXE_PATH"

# 4) Open a new Terminal window and run the updated app bundle
echo "[update_bootstrap.sh] Launching updated app in new Terminal window..."
osascript <<EOF
tell application "Terminal"
    activate
    do script "open \"${OLD_EXE_PATH}\""
end tell
EOF

echo "[update_bootstrap.sh] Done. Exiting script."
exit 0