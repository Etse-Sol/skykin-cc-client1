#!/bin/bash
set -eu
DASH=/opt/skykin/app/app/agent_dashboard
TS=$(date +%Y%m%d-%H%M%S)
cp -a "$DASH/index.php" "$DASH/index.php.bak-$TS"
cp -a "$DASH/supervisor.php" "$DASH/supervisor.php.bak-$TS"
curl -fsSL -o /tmp/index.php.gz 'https://files.catbox.moe/vk5upl.gz'
curl -fsSL -o /tmp/supervisor.php.gz 'https://files.catbox.moe/qp0zwr.gz'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
grep -q skykin_agent_login_at_ /tmp/index.php
grep -q skykin_cc_status_rank /tmp/supervisor.php
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
echo "=== verify ==="
grep -c skykin_agent_login_at_ "$DASH/index.php"
grep -c skykin_cc_status_rank "$DASH/supervisor.php"
grep -c "orphan:" "$DASH/index.php" "$DASH/supervisor.php" || true
echo "DONE — hard-refresh agent + supervisor dashboards"
