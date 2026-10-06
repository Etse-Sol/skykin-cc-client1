#!/bin/bash
set -eu
echo "=== Sync supervisor softphone + agent status clear ==="
curl -fsSL -o /tmp/supervisor.php.gz 'https://files.catbox.moe/rx0jqc.gz'
curl -fsSL -o /tmp/index.php.gz 'https://files.catbox.moe/eoixnw.gz'
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/index.php.gz > /tmp/index.php
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
install -m 0644 /tmp/index.php "$DASH/index.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_SUP_OUT_v1 "$DASH/supervisor.php"
grep -c SKYKIN_OUT_RING_v5 "$DASH/index.php"
grep -c skykinRestoreRegisteredStatus "$DASH/index.php"
echo DONE
