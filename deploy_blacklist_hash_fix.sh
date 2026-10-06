#!/bin/bash
# Deploy blacklist hash-clear fix + wipe orphan keys for 911528271
set -euo pipefail
WEB=/var/www/fusionpbx/app/agent_dashboard
# Copy from wherever you staged the files, or from this host path after scp:
#   skykin_bl_sync.php  skykin_config.php  -> skykin-web:$WEB/

if [ -f /tmp/skykin_bl_sync.php ]; then
  docker cp /tmp/skykin_bl_sync.php skykin-web:$WEB/skykin_bl_sync.php
fi
if [ -f /tmp/skykin_config.php ]; then
  docker cp /tmp/skykin_config.php skykin-web:$WEB/skykin_config.php
fi

docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true

# One-time: clear orphan hash for the call that was 603'd; keep 946289866
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env | cut -d= -f2-)
FS(){ docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1"; }
for k in 911528271 0911528271 251911528271 1528271 11528271; do
  FS "hash delete/skykin_bl/ahununu~$k"
  FS "hash delete/skykin_bl/$k"
done
# Rebuild hash from DB (keeps only real rows)
docker exec skykin-web php -r '
require "/var/www/fusionpbx/app/agent_dashboard/skykin_config.php";
$db = skykin_pdo_fusionpbx();
require_once "/var/www/fusionpbx/app/agent_dashboard/skykin_bl_sync.php";
skykin_bl_push($db);
echo "push ok\n";
'

echo "verify orphans gone:"
for k in 911528271 946289866; do
  echo -n "ahununu~$k -> "; FS "hash select/skykin_bl/ahununu~$k"
done
echo DONE
