#!/bin/bash
set -eu
echo "=== KPI Inbound/Outbound split (agent + supervisor) ==="
curl -fsSL -o /tmp/index.php.gz 'https://files.catbox.moe/f8a5cg.gz'
curl -fsSL -o /tmp/supervisor.php.gz 'https://files.catbox.moe/3q3c1a.gz'
curl -fsSL -o /tmp/skykin_config.php.gz 'https://files.catbox.moe/vkdfqu.gz'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/skykin_config.php.gz > /tmp/skykin_config.php
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
install -m 0644 /tmp/skykin_config.php "$DASH/skykin_config.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_AGENT_KPI_IN_OUT_v1 "$DASH/index.php"
grep -c SKYKIN_KPI_IN_OUT_v1 "$DASH/supervisor.php"
grep -c answered_inbound "$DASH/skykin_config.php"
echo DONE
