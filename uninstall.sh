#!/bin/zsh
set -euo pipefail

LABEL="com.fixmyback.sittimer"
PLIST_DST="$HOME/Library/LaunchAgents/com.fixmyback.sittimer.plist"

launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
rm -f "$PLIST_DST"

echo "FixMyBack stopped and will not auto-start anymore."
