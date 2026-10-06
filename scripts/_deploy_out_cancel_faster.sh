#!/bin/bash
set -eu
echo "=== Outbound fail-guard: 2.5s + 3 ticks (v7/v3) ==="
curl -fsSL -o /tmp/index.php.gz 'https://files.catbox.moe/jhspgp.gz'
curl -fsSL -o /tmp/supervisor.php.gz 'https://files.catbox.moe/4h9gay.gz'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_OUT_RING_v7 "$DASH/index.php"
grep -c SKYKIN_SUP_OUT_v3 "$DASH/supervisor.php"
grep -c 'ageMs >= 2500' "$DASH/index.php"
grep -c '_outDeclineTicks >= 3' "$DASH/index.php"
echo DONE
