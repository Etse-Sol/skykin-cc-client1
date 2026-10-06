#!/bin/bash
set -eu
echo "=== Faster outbound aim 1-2s (ICE 400ms + warm + lua) ==="
curl -fsSL -o /tmp/index.php.gz 'https://files.catbox.moe/4yw0c1.gz'
curl -fsSL -o /tmp/supervisor.php.gz 'https://files.catbox.moe/1ehxac.gz'
curl -fsSL -o /tmp/skykin_outbound.lua.gz 'https://files.catbox.moe/84njwd.gz'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/skykin_outbound.lua.gz > /tmp/skykin_outbound.lua
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
cp /tmp/skykin_outbound.lua /opt/skykin/fs-live/skykin_outbound.lua
cp /tmp/skykin_outbound.lua /opt/skykin/fs-config/skykin_outbound.lua 2>/dev/null || true
docker cp /tmp/skykin_outbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_outbound.lua
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_OUT_RING_v9 "$DASH/index.php"
grep -c SKYKIN_SUP_OUT_v5 "$DASH/supervisor.php"
grep -c SKYKIN_ICE_FAST_v2 "$DASH/index.php"
docker exec skykin-freeswitch grep -c bgapi /etc/freeswitch/scripts/skykin_outbound.lua
echo DONE
