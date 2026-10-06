#!/bin/bash
set -eu
echo "=== Supervisor KPIs: Inbound + Outbound split ==="
curl -fsSL -o /tmp/supervisor.php.gz 'https://files.catbox.moe/3q3c1a.gz'
curl -fsSL -o /tmp/skykin_config.php.gz 'https://files.catbox.moe/vkdfqu.gz'
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/skykin_config.php.gz > /tmp/skykin_config.php
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
install -m 0644 /tmp/skykin_config.php "$DASH/skykin_config.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_KPI_IN_OUT_v1 "$DASH/supervisor.php"
grep -c answered_inbound "$DASH/skykin_config.php"
grep -c 'Outbound Today' "$DASH/supervisor.php"
echo DONE
