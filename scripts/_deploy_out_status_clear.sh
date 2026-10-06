#!/bin/bash
set -eu
echo "=== Fix stuck Call ended status (SIP 487) ==="
curl -fsSL -o /tmp/index.php.gz 'https://files.catbox.moe/eoixnw.gz'
gzip -dc /tmp/index.php.gz > /tmp/index.php
install -m 0644 /tmp/index.php /opt/skykin/app/app/agent_dashboard/index.php
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_OUT_RING_v5 /opt/skykin/app/app/agent_dashboard/index.php
grep -c skykinRestoreRegisteredStatus /opt/skykin/app/app/agent_dashboard/index.php
echo DONE
