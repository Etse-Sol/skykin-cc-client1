#!/bin/bash
set -eu
echo "=== Deploy outbound call classification ==="
curl -fsSL -o /tmp/index.php.gz 'https://files.catbox.moe/socch1.gz'
curl -fsSL -o /tmp/skykin_config.php.gz 'https://files.catbox.moe/zfseir.gz'
curl -fsSL -o /tmp/supervisor.php.gz 'https://files.catbox.moe/swlsu5.gz'
curl -fsSL -o /tmp/skykin_outbound.lua.gz 'https://files.catbox.moe/tbfia8.gz'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/skykin_config.php.gz > /tmp/skykin_config.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/skykin_outbound.lua.gz > /tmp/skykin_outbound.lua

DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/skykin_config.php "$DASH/skykin_config.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true

mkdir -p /opt/skykin/fs-live
cp /tmp/skykin_outbound.lua /opt/skykin/fs-live/skykin_outbound.lua
cp /tmp/skykin_outbound.lua /opt/skykin/fs-config/skykin_outbound.lua 2>/dev/null || true
docker cp /tmp/skykin_outbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_outbound.lua

echo "=== Verify ==="
grep -c skykin_outbound_fail_label "$DASH/skykin_config.php"
grep -c skykinOutboundFailLabel "$DASH/index.php"
grep -c playOutboundFailTone "$DASH/index.php"
docker exec skykin-freeswitch grep -c 'hangup agent cause' /etc/freeswitch/scripts/skykin_outbound.lua
echo "DONE — hard-refresh agent + supervisor dashboards"
echo "Live call: Busy / No answer tones. History Status: Busy, No answer / switched off, etc."
