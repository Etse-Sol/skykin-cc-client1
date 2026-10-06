#!/bin/bash
set -eu
echo "=== Harden outbound: stop ORIGINATOR_CANCEL right after Call ==="
curl -fsSL -o /tmp/index.php.gz 'https://files.catbox.moe/bze89f.gz'
curl -fsSL -o /tmp/supervisor.php.gz 'https://files.catbox.moe/xb9r3k.gz'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_OUT_RING_v6 "$DASH/index.php"
grep -c SKYKIN_SUP_OUT_v2 "$DASH/supervisor.php"
grep -c '_outDeclineTicks >= 5' "$DASH/index.php"
grep -c 'ageMs >= 4000' "$DASH/index.php"
echo DONE
