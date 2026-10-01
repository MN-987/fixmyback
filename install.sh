#!/bin/zsh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SRC="$DIR/com.fixmyback.sittimer.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.fixmyback.sittimer.plist"
LABEL="com.fixmyback.sittimer"

chmod +x "$DIR/sit_timer.py"
mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$HOME/Library/Logs"

cp "$PLIST_SRC" "$PLIST_DST"

launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "FixMyBack is running in the background."
echo "It will start again every time you log in."
echo "Logs: $HOME/Library/Logs/fixmyback.log"
echo
echo "Try it now:  python3 $DIR/sit_timer.py --test"
echo "Stop it:     $DIR/uninstall.sh"
