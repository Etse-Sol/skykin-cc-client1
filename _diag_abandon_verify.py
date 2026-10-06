#!/usr/bin/env python3
"""Verify Abandoned vs Answer-failure from ecs-cc server evidence."""
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    username="root",
    password="Pass@1234",
    timeout=25,
    allow_agent=False,
    look_for_keys=False,
)


def run(cmd, timeout=180):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== containers ===")
print(run("docker ps --format '{{.Names}}' | head -20"))

print("==== CDR hour summary today (Africa/Addis_Ababa) ===")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT
  to_char(start_stamp AT TIME ZONE 'Africa/Addis_Ababa', 'HH24') AS hh,
  COUNT(*) FILTER (
    WHERE LOWER(COALESCE(direction,'')) = 'inbound'
      AND billsec > 0
      AND destination_number ~ '11619803'
  ) AS in_with_billsec,
  COUNT(*) FILTER (
    WHERE LOWER(COALESCE(direction,'')) = 'inbound'
      AND billsec = 0
      AND destination_number ~ '11619803'
  ) AS in_zero_bill,
  COUNT(*) FILTER (
    WHERE hangup_cause = 'NORMAL_TEMPORARY_FAILURE'
  ) AS temp_fail,
  COUNT(*) FILTER (
    WHERE hangup_cause = 'ORIGINATOR_CANCEL'
      AND LOWER(COALESCE(direction,'')) = 'outbound'
  ) AS out_cancel,
  ROUND(AVG(waitsec) FILTER (
    WHERE LOWER(COALESCE(direction,'')) = 'inbound'
      AND billsec > 0
      AND destination_number ~ '11619803'
  )::numeric, 1) AS avg_waitsec
FROM v_xml_cdr
WHERE (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::date = CURRENT_DATE
GROUP BY 1
ORDER BY 1;
"
"""
    )
)

print("==== sample Abandoned-like rows 14:00-14:25 (DID legs) ===")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT
  to_char(start_stamp AT TIME ZONE 'Africa/Addis_Ababa', 'HH24:MI:SS') AS t,
  caller_id_number,
  destination_number,
  billsec,
  waitsec,
  hangup_cause,
  LEFT(COALESCE(cc_agent,''),40) AS cc_agent,
  LEFT(COALESCE(last_arg,''),50) AS last_arg,
  LEFT(COALESCE(cc_cancel_reason,''),30) AS cc_cancel
FROM v_xml_cdr
WHERE (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::date = CURRENT_DATE
  AND (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::time BETWEEN '14:00:00' AND '14:25:00'
  AND LOWER(COALESCE(direction,'')) = 'inbound'
  AND destination_number ~ '11619803'
ORDER BY start_stamp
LIMIT 40;
"
"""
    )
)

print("==== 10:20-10:40 Missed window ===")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT
  to_char(start_stamp AT TIME ZONE 'Africa/Addis_Ababa', 'HH24:MI:SS') AS t,
  caller_id_number,
  destination_number,
  billsec,
  duration,
  hangup_cause,
  LEFT(COALESCE(last_arg,''),50) AS last_arg
FROM v_xml_cdr
WHERE (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::date = CURRENT_DATE
  AND (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::time BETWEEN '10:20:00' AND '10:40:00'
  AND LOWER(COALESCE(direction,'')) = 'inbound'
  AND destination_number ~ '11619803'
ORDER BY start_stamp
LIMIT 40;
"
"""
    )
)

print("==== FS log: DTLS / Answer fail / TEMPORARY around 10:20-14:30 ===")
print(
    run(
        r"""docker exec skykin-freeswitch sh -c '
for f in /var/log/freeswitch/freeswitch.log /usr/local/freeswitch/log/freeswitch.log; do
  [ -f "$f" ] && echo "LOG=$f" && ls -lh "$f"
done
# count key failure signatures in today-ish log
LOG=$(ls -1 /var/log/freeswitch/freeswitch.log /usr/local/freeswitch/log/freeswitch.log 2>/dev/null | head -1)
if [ -n "$LOG" ]; then
  echo "---- DTLS / fingerprint / TEMPORARY_FAILURE counts (whole current log) ----"
  grep -c "DTLS" "$LOG" 2>/dev/null || true
  grep -c "fingerprint" "$LOG" 2>/dev/null || true
  grep -c "NORMAL_TEMPORARY_FAILURE" "$LOG" 2>/dev/null || true
  echo "---- sample lines with TEMPORARY / DTLS / no agents / queue ----"
  grep -E "NORMAL_TEMPORARY_FAILURE|DTLS handshake|fingerprint|no agents|QUEUE|cc_member|skykin_inbound|Waiting for agent" "$LOG" 2>/dev/null | tail -80
fi
'
"""
    )
)

print("==== agent status events 11-14 if any ===")
print(
    run(
        r"""docker exec skykin-freeswitch sh -c '
LOG=$(ls -1 /var/log/freeswitch/freeswitch.log /usr/local/freeswitch/log/freeswitch.log 2>/dev/null | head -1)
grep -E "callcenter.*Agent.*(Available|Logged Out|On Break|Receiving)|cc_agent_state" "$LOG" 2>/dev/null | tail -60
'
"""
    )
)

c.close()
print("DONE")
