#!/bin/bash
set -eu
echo "=== Deploy outbound cause labels + ringback ==="
curl -fsSL -o /tmp/index.php.gz https://files.catbox.moe/jnh8cy.gz
curl -fsSL -o /tmp/skykin_outbound.lua.gz https://files.catbox.moe/dwy40g.gz
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/skykin_outbound.lua.gz > /tmp/skykin_outbound.lua

install -m 0644 /tmp/index.php /opt/skykin/app/app/agent_dashboard/index.php
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true

mkdir -p /opt/skykin/fs-live
cp /tmp/skykin_outbound.lua /opt/skykin/fs-live/skykin_outbound.lua
cp /tmp/skykin_outbound.lua /opt/skykin/fs-config/skykin_outbound.lua 2>/dev/null || true
docker cp /tmp/skykin_outbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_outbound.lua

echo "=== Verify ==="
grep -c skykinOutboundFailLabel /opt/skykin/app/app/agent_dashboard/index.php
grep -c hangup_cause /opt/skykin/app/app/agent_dashboard/index.php
docker exec skykin-freeswitch grep -n "hangup agent cause\|Propagate the real B-leg" /etc/freeswitch/scripts/skykin_outbound.lua | head -5
echo "DONE — hard-refresh agent dashboard, then test Busy / off / ringing"
