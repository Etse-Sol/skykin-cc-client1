#!/bin/bash
# Deploy Agent-1 break sync fix (supervisor + agent dashboard).
# Does NOT remove duplicate FS agents — updates both so Live Status matches.
set -eu
DASH="${DASH:-/var/www/fusionpbx/app/agent_dashboard}"
# common alternate path
if [ ! -d "$DASH" ]; then
  DASH="/usr/share/fusionpbx/app/agent_dashboard"
fi
if [ ! -d "$DASH" ]; then
  echo "Find dashboard dir:"; find /var/www /usr/share /opt -type d -name agent_dashboard 2>/dev/null | head
  exit 1
fi
TS=$(date +%Y%m%d-%H%M%S)
cp -a "$DASH/supervisor.php" "$DASH/supervisor.php.bak-break-$TS"
cp -a "$DASH/index.php" "$DASH/index.php.bak-break-$TS"
# Expect files already placed next to this script or in /tmp
SRC="${1:-/tmp}"
cp -a "$SRC/supervisor.php" "$DASH/supervisor.php"
cp -a "$SRC/index.php" "$DASH/index.php"
grep -n "skykin_cc_status_rank\|Orphan FS\|orphan:" "$DASH/supervisor.php" | head -10
grep -n "Orphan FS\|orphan:" "$DASH/index.php" | head -10
echo "DONE — hard-refresh supervisor + Agent 1, approve a break, confirm both show Break."
