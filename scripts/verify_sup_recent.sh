#!/bin/bash
# Verify + re-apply supervisor Recent dials. LF only.
set -eu
echo "===== on server now ====="
docker exec skykin-web grep -n "toggleRecentDials\|dp-recent\|RememberRecent\|Recent" \
  /var/www/fusionpbx/app/agent_dashboard/supervisor.php | head -20 || echo "(not found)"

echo
echo "===== dial pad HTML snippet ====="
docker exec skykin-web grep -n "dp-row-actions\|dp-call\|dp-recent\|dpRecentList" \
  /var/www/fusionpbx/app/agent_dashboard/supervisor.php | head -20
