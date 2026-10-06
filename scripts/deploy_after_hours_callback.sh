#!/bin/bash
# Deploy after-hours → Callbacks auto-save. No FreeSWITCH restart.
# LF only. Fixes host-network FS (cannot reach http://web/).
set -eu

WEB_PHP=/var/www/fusionpbx/app/agent_dashboard
FS_LIVE=/opt/skykin/fs-live
KEY=skykin-ah-cb-2026

echo "=== 1) PHP endpoint ==="
if [ ! -f /tmp/skykin_after_hours_cb.php ]; then
  echo "Missing /tmp/skykin_after_hours_cb.php — use full catbox installer"
  exit 1
fi
docker cp /tmp/skykin_after_hours_cb.php skykin-web:$WEB_PHP/skykin_after_hours_cb.php
docker exec skykin-web chmod 644 $WEB_PHP/skykin_after_hours_cb.php

echo "=== 2) Patch list_callbacks (show after-hours to agents) ==="
docker exec skykin-web php -r '
$path="/var/www/fusionpbx/app/agent_dashboard/index.php";
$s=file_get_contents($path);
$old="WHERE agent_id = :agent AND status = '\''Scheduled'\''";
$new="WHERE status = '\''Scheduled'\''\n                  AND (agent_id = :agent OR agent_id = '\''after-hours'\'')";
if (strpos($s,$new)!==false) { echo "list_callbacks already patched\n"; exit(0); }
if (strpos($s,$old)===false) { echo "WARN: list_callbacks pattern not found\n"; exit(0); }
$s=str_replace($old,$new,$s);
file_put_contents($path,$s);
echo "list_callbacks patched\n";
'

echo "=== 3) Lua inbound (after-hours save → 127.0.0.1:8190 + file queue) ==="
if [ ! -f /tmp/skykin_inbound.lua ]; then
  echo "Missing /tmp/skykin_inbound.lua"
  exit 1
fi
mkdir -p "$FS_LIVE"
cp /tmp/skykin_inbound.lua "$FS_LIVE/skykin_inbound.lua"
docker cp /tmp/skykin_inbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
# Also overlay path used on some hosts
if [ -d /opt/skykin/fs-config ]; then
  cp /tmp/skykin_inbound.lua /opt/skykin/fs-config/skykin_inbound.lua 2>/dev/null || true
fi

echo "=== 4) Ensure mod_curl loaded (best-effort) ==="
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env 2>/dev/null | cut -d= -f2- || true)
if [ -z "$PW" ]; then PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/.env 2>/dev/null | cut -d= -f2- || true); fi
if [ -n "${PW:-}" ]; then
  docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "load mod_curl" 2>/dev/null || true
else
  docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -x "load mod_curl" 2>/dev/null || true
fi

echo "=== 5) Cron drain file queue every 5 min ==="
mkdir -p /opt/skykin/fraud-alert
cat > /opt/skykin/fraud-alert/drain_ah_cb.sh <<'EOS'
#!/bin/bash
# Drain shared-volume queue written by host-network FreeSWITCH.
KEY=skykin-ah-cb-2026
for port in 8190 8080 8090; do
  if curl -fsS --max-time 3 "http://127.0.0.1:${port}/app/agent_dashboard/skykin_after_hours_cb.php?key=${KEY}&drain=1" >/tmp/ah_cb_drain.json 2>/dev/null; then
    cat /tmp/ah_cb_drain.json
    exit 0
  fi
done
docker exec -e QUERY_STRING="key=${KEY}&drain=1" -e REQUEST_METHOD=GET skykin-web \
  php -r 'parse_str(getenv("QUERY_STRING")?:"", $_GET); include "/var/www/fusionpbx/app/agent_dashboard/skykin_after_hours_cb.php";' \
  2>/dev/null || true
EOS
chmod +x /opt/skykin/fraud-alert/drain_ah_cb.sh
cat > /etc/cron.d/skykin-after-hours-cb <<'EOF'
*/5 * * * * root /opt/skykin/fraud-alert/drain_ah_cb.sh >/dev/null 2>&1
EOF

echo "=== 6) Smoke test PHP insert via published HTTP (host net) ==="
SMOKE_OK=0
for port in 8190 8080 8090; do
  if curl -fsS --max-time 5 \
    "http://127.0.0.1:${port}/app/agent_dashboard/skykin_after_hours_cb.php?key=${KEY}&phone=%2B251900000099&domain=ahununu&did=smoke&uuid=smoke-$(date +%s)" \
    | tee /tmp/ah_cb_smoke.json | grep -q '"ok":true'; then
    echo "HTTP OK on port $port"
    SMOKE_OK=1
    break
  fi
done
if [ "$SMOKE_OK" != 1 ]; then
  echo "WARN: host HTTP smoke failed — trying docker php include"
  docker exec skykin-web php -r '
$_GET=["key"=>"skykin-ah-cb-2026","phone"=>"+251900000099","domain"=>"ahununu","did"=>"test","uuid"=>"smoke"];
include "/var/www/fusionpbx/app/agent_dashboard/skykin_after_hours_cb.php";
'
  echo
fi

echo "=== 7) Drain any queued file now ==="
/opt/skykin/fraud-alert/drain_ah_cb.sh || true
echo

echo "=== 8) Backfill last 48h after-hours CIDs from FS logs (if any) ==="
docker exec skykin-freeswitch sh -c 'grep -h "skykin after-hours drop" /var/log/freeswitch/freeswitch.log* 2>/dev/null | tail -200' \
  > /tmp/ah_drops.txt 2>/dev/null || true
python3 - <<'PY'
import re, subprocess, urllib.parse, urllib.request, os
from pathlib import Path
text = Path("/tmp/ah_drops.txt").read_text(errors="replace") if Path("/tmp/ah_drops.txt").exists() else ""
# cid=+2519... or cid=09...
cids = []
for m in re.finditer(r"after-hours drop domain=(\S+)\s+cid=(\S+)", text):
    domain, cid = m.group(1), m.group(2).rstrip("\\n")
    cids.append((domain, cid))
# unique preserve order
seen=set(); uniq=[]
for d,c in cids:
    k=(d,c)
    if k in seen: continue
    seen.add(k); uniq.append(k)
print(f"found {len(uniq)} unique after-hours CIDs in logs")
key="skykin-ah-cb-2026"
ok=0
for domain, cid in uniq[-80:]:
    q=urllib.parse.urlencode({"key":key,"phone":cid,"domain":domain,"did":"log-backfill","uuid":"log"})
    body=None
    for port in (8190,8080,8090):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/app/agent_dashboard/skykin_after_hours_cb.php?{q}", timeout=5) as r:
                body=r.read().decode()
            break
        except Exception:
            body=None
    if body and '"ok":true' in body.replace(" ",""):
        ok += 1
    elif body and '"ok": true' in body:
        ok += 1
print(f"backfill ok/dedup responses: {ok}")
PY

echo "=== 9) Verify Lua snippet ==="
docker exec skykin-freeswitch grep -n "127.0.0.1:8190\|skykin_after_hours_queue\|after-hours callback" \
  /etc/freeswitch/scripts/skykin_inbound.lua | head -25

echo
echo "DONE — after-hours callers save via http://127.0.0.1:8190 + shared file queue."
echo "No FS restart. New after-hours calls auto-save before call-end-2."
echo "Refresh Callbacks tab (agent or supervisor)."
