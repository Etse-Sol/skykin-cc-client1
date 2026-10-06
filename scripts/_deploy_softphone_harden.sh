#!/bin/bash
set -eu
echo "=== Softphone harden v1 (keepalive + cooldown + optional SRTP) ==="
curl -fsSL -o /tmp/index.php.gz 'https://files.catbox.moe/pxbv7w.gz'
curl -fsSL -o /tmp/supervisor.php.gz 'https://files.catbox.moe/h4kqhl.gz'
curl -fsSL -o /tmp/skykin_inbound.lua.gz 'https://files.catbox.moe/vs5ewc.gz'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/skykin_inbound.lua.gz > /tmp/skykin_inbound.lua
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
cp /tmp/skykin_inbound.lua /opt/skykin/fs-live/skykin_inbound.lua
cp /tmp/skykin_inbound.lua /opt/skykin/fs-config/skykin_inbound.lua 2>/dev/null || true
docker cp /tmp/skykin_inbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_SOFTPHONE_HARDEN_v1 "$DASH/index.php"
grep -c SKYKIN_SOFTPHONE_HARDEN_v1 "$DASH/supervisor.php"
grep -c SKYKIN_SOFTPHONE_HARDEN_v1 /opt/skykin/fs-live/skykin_inbound.lua
grep -c 'tech-fail cooldown 90s' /opt/skykin/fs-live/skykin_inbound.lua
grep -c 'rtp_secure_media=optional' /opt/skykin/fs-live/skykin_inbound.lua
echo DONE
