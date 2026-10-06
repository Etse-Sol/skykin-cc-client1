#!/bin/bash
# Run on ecs-cc: recent Agent1 / 101 activity (last 20 min)
set -eu
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env | cut -d= -f2-)
FS() { docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1"; }

echo "=== Clock ==="
date
echo

echo "=== CDR last 20 min involving 101 / Agent1 (ahununu) ==="
docker exec skykin-web bash -c '
export PGPASSWORD="${DB_PASSWORD:-}"
# try common env
if [ -f /opt/skykin/app/.env ]; then set -a; . /opt/skykin/app/.env 2>/dev/null; set +a; fi
' 2>/dev/null || true

# Query via container that has psql + fusionpbx DB
docker exec -i skykin-web bash <<'EOS' || docker exec -i skykin-db bash <<'EOS2' || true
set -e
# discover connection from env files on host mounted paths
ENVF=/var/www/fusionpbx 2>/dev/null
psql -U fusionpbx -d fusionpbx -c "SELECT 1" 2>/dev/null && DBOK=1 || true
EOS
EOS2

# Direct approach used on ecs-cc installs
python3 - <<'PY'
import os, subprocess, sys
from datetime import datetime, timedelta, timezone
# Prefer docker exec into postgres
cmds = [
  ["docker","exec","-i","skykin-db","psql","-U","fusionpbx","-d","fusionpbx","-t","-A","-F","|"],
  ["docker","exec","-i","skykin-postgres","psql","-U","fusionpbx","-d","fusionpbx","-t","-A","-F","|"],
  ["docker","exec","-i","skykin-web","psql","-U","fusionpbx","-d","fusionpbx","-t","-A","-F","|"],
]
sql = r"""
SELECT to_char(to_timestamp(start_epoch), 'YYYY-MM-DD HH24:MI:SS') AS started,
       direction,
       caller_id_number,
       destination_number,
       billsec,
       duration,
       hangup_cause,
       LEFT(COALESCE(last_arg,''), 60) AS last_arg
FROM v_xml_cdr
WHERE start_epoch >= EXTRACT(EPOCH FROM NOW() - INTERVAL '20 minutes')::bigint
  AND (
    destination_number LIKE '%101%'
    OR caller_id_number LIKE '%101%'
    OR last_arg ILIKE '%101%'
    OR cc_agent ILIKE '%101%'
    OR presence_id ILIKE '%101%'
  )
ORDER BY start_epoch DESC
LIMIT 40;
"""
for cmd in cmds:
  try:
    p = subprocess.run(cmd + ["-c", sql], capture_output=True, text=True, timeout=30)
    if p.returncode == 0:
      out = (p.stdout or "").strip()
      print(out if out else "(no CDR rows for 101 in last 20 min)")
      if p.stderr.strip():
        print("stderr:", p.stderr.strip()[:200])
      break
  except Exception as e:
    continue
else:
  print("Could not query DB via docker psql — trying grep logs only")
PY

echo
echo "=== FreeSWITCH log mentions of 101 / RING in last ~20 min ==="
# container log + host journal-ish
docker logs skykin-freeswitch --since 20m 2>&1 | grep -E '101|RINGING|callcenter|EXECUTE.*bridge|sofia/internal/101' | tail -80 || echo "(no docker log matches)"

echo
echo "=== DONE ==="
