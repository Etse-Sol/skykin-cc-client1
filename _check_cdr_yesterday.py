#!/usr/bin/env python3
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CMD = r"""
set -e
echo "=== db container ==="
docker ps --format '{{.Names}}' | head -20

DB=$(docker ps --format '{{.Names}}' | grep -E 'skykin-db|postgres' | head -1)
echo "DB=$DB"

# Try common creds
run_sql() {
  local sql="$1"
  docker exec "$DB" psql -U fusionpbx -d fusionpbx -c "$sql" 2>/dev/null \
    || docker exec "$DB" psql -U postgres -d fusionpbx -c "$sql" 2>/dev/null \
    || docker exec -e PGPASSWORD=fusionpbx "$DB" psql -U fusionpbx -d fusionpbx -c "$sql"
}

echo "=== domains last 2 days ==="
run_sql "SELECT domain_name, count(*) FROM v_xml_cdr WHERE start_stamp >= CURRENT_DATE - 1 GROUP BY 1 ORDER BY 2 DESC;"

echo "=== yesterday summary ==="
run_sql "SELECT count(*) AS total,
  count(*) FILTER (WHERE direction='inbound') AS inbound,
  count(*) FILTER (WHERE direction='outbound') AS outbound,
  count(*) FILTER (WHERE COALESCE(billsec,0)>0) AS with_billsec,
  count(*) FILTER (WHERE hangup_cause ILIKE '%NO_ANSWER%' OR hangup_cause ILIKE '%ORIGINATOR_CANCEL%' OR hangup_cause ILIKE '%CALL_REJECTED%') AS cancel_reject
FROM v_xml_cdr WHERE start_stamp::date = CURRENT_DATE - 1;"

echo "=== yesterday rows (latest 50) ==="
run_sql "SELECT to_char(start_stamp,'YYYY-MM-DD HH24:MI:SS') AS t,
  direction, caller_id_number AS caller, destination_number AS dest,
  hangup_cause, COALESCE(billsec,0) AS bill, COALESCE(waitsec,0) AS wait, COALESCE(duration,0) AS dur
FROM v_xml_cdr
WHERE start_stamp::date = CURRENT_DATE - 1
ORDER BY start_stamp DESC
LIMIT 50;"

echo "=== FS log yesterday invites (sample) ==="
docker exec skykin-freeswitch sh -c 'grep -E "receiving invite|skykin inbound answer|skykin inbound try" /var/log/freeswitch/freeswitch.log 2>/dev/null | grep "2026-09-17" | tail -40'
"""

targets = [
    ("196.189.236.140", 30, "Pass@1234"),
    ("196.189.236.140", 22, "Pass@1234"),
    ("10.0.0.77", 22, "Pass@1234"),
]

for host, port, pw in targets:
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(
            host,
            port=port,
            username="root",
            password=pw,
            timeout=15,
            banner_timeout=15,
            auth_timeout=15,
            allow_agent=False,
            look_for_keys=False,
        )
        print(f"CONNECTED {host}:{port}")
        _, stdout, stderr = c.exec_command(CMD, timeout=90)
        print(stdout.read().decode("utf-8", "replace"))
        err = stderr.read().decode("utf-8", "replace").strip()
        if err:
            print("[stderr]", err[:800])
        c.close()
        sys.exit(0)
    except Exception as e:
        print(f"FAIL {host}:{port} {type(e).__name__}: {e}")

print("NO_SSH")
sys.exit(1)
