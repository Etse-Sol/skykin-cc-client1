#!/bin/sh
# Run on the PBX host after: git pull origin 5.5
# Does not change inbound.lua early-answer except hunt filter already in repo lua.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
WEB_DASH=/var/www/fusionpbx/app/agent_dashboard
HOST_DASH=/opt/skykin/skykin-cc-client1/app/agent_dashboard
CONF=/etc/nginx/sites-available/skykin.conf

echo "repo $ROOT"

if [ -d "$ROOT/skyconnect" ] && command -v npm >/dev/null 2>&1; then
  echo "=== build SPA ==="
  (cd "$ROOT/skyconnect" && npm run build)
fi

copy_php() {
  dest="$1"
  mkdir -p "$dest"
  for f in skyconnect_ops.php evaluation.php crm.php skykin_ai.php skykin_config.php reports.php \
           skyconnect_omni.php skyconnect_omni_lib.php skyconnect_session.php skyconnect_signin.php \
           skyconnect_land.php skykin_do_login.php; do
    [ -f "$ROOT/app/agent_dashboard/$f" ] && cp -a "$ROOT/app/agent_dashboard/$f" "$dest/"
  done
}

echo "=== PHP on host tree ==="
if [ -d "$HOST_DASH" ] || mkdir -p "$HOST_DASH" 2>/dev/null; then
  copy_php "$HOST_DASH"
fi

echo "=== PHP + SPA into skykin-web ==="
if docker ps --format '{{.Names}}' | grep -qx skykin-web; then
  docker exec skykin-web mkdir -p "$WEB_DASH/skyconnect"
  copy_php /tmp/sc-php-host
  docker cp /tmp/sc-php-host/. skykin-web:"$WEB_DASH/"
  if [ -f "$ROOT/skyconnect/dist/index.html" ]; then
    docker cp "$ROOT/skyconnect/dist/." skykin-web:"$WEB_DASH/skyconnect/"
    echo "SPA copied"
  else
    echo "NO SPA dist — run npm run build in skyconnect/ then re-run this script"
  fi
  GW=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.Gateway}} {{end}}' skykin-web | awk '{print $1}')
  [ -z "$GW" ] && GW=172.18.0.1
  mkdir -p /etc/skykin
  if [ ! -f /etc/skykin/ai.env ]; then
    printf 'SKYKIN_AI=on\nSKYKIN_AI_MODE=skykin\nSKYKIN_AI_BASE_URL=http://%s:8100\n' "$GW" > /etc/skykin/ai.env
  fi
  docker exec skykin-web mkdir -p /etc/skykin || true
  docker cp /etc/skykin/ai.env skykin-web:/etc/skykin/ai.env || true
else
  echo "skykin-web not running"
fi

echo "=== A2A + hunt lua ==="
if [ -x "$ROOT/scripts/paste_a2a_webrtc.sh" ] || [ -f "$ROOT/scripts/paste_a2a_webrtc.sh" ]; then
  sh "$ROOT/scripts/paste_a2a_webrtc.sh" || true
fi

echo "=== AI :8100 ==="
if command -v ss >/dev/null 2>&1 && ss -lntp | grep -q ':8100'; then
  echo "AI already listening"
else
  echo "Start AI in another terminal:"
  echo "  cd $ROOT/tools/skykin_ai_local && SKYKIN_AI_HOST=0.0.0.0 python3 server.py"
fi

echo "Open https://$(hostname -I 2>/dev/null | awk '{print $1}')/app/agent_dashboard/skyconnect/"
echo "DONE"
