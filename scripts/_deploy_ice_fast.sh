#!/bin/bash
set -eu
echo "=== Faster outbound: ICE 3s to 1s ==="
curl -fsSL -o /tmp/index.php.gz 'https://files.catbox.moe/odljc3.gz'
curl -fsSL -o /tmp/supervisor.php.gz 'https://files.catbox.moe/i2iarj.gz'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_OUT_RING_v8 "$DASH/index.php"
grep -c SKYKIN_SUP_OUT_v4 "$DASH/supervisor.php"
grep -c SKYKIN_ICE_FAST_v1 "$DASH/index.php"
grep -c 'ICE_GATHERING_TIMEOUT_MS = 1000' "$DASH/index.php"
echo DONE
