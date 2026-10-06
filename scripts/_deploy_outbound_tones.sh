#!/bin/bash
set -eu
echo "=== Deploy outbound audible tones (ring/busy) ==="
curl -fsSL -o /tmp/index.php.gz https://files.catbox.moe/07eyu6.gz
gzip -dc /tmp/index.php.gz > /tmp/index.php
install -m 0644 /tmp/index.php /opt/skykin/app/app/agent_dashboard/index.php
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
echo "=== Verify ==="
grep -c playOutboundFailTone /opt/skykin/app/app/agent_dashboard/index.php
grep -c startBusyTone /opt/skykin/app/app/agent_dashboard/index.php
grep -c startCongestionTone /opt/skykin/app/app/agent_dashboard/index.php
echo "DONE — hard-refresh agent dashboard, then dial: hear ring while calling, busy tone if busy"
