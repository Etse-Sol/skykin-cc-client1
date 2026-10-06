#!/usr/bin/env python3
"""Check outbound ring delay: dialplan, lua, recent FS log timing."""
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    port=30,
    username="root",
    password="Pass@1234",
    timeout=25,
    allow_agent=False,
    look_for_keys=False,
)


def run(cmd, timeout=90):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== 1) outbound lua (sleep/delay?) ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "'grep -nE \"sleep|delay|bridge|instant_ringback|ignore_early|originate\" "
        "/etc/freeswitch/scripts/skykin_outbound.lua'"
    )
)

print("==== 2) dialplan outbound paths ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "'grep -rnE \"skykin_outbound|outbound|sleep|sleep\\(\" "
        "/etc/freeswitch/dialplan/ 2>/dev/null | grep -iE \"ahununu|skykin|outbound|sleep\" | head -40'"
    )
)

print("==== 3) recent outbound timing from FS log ====")
print(
    run(
        r"""docker exec skykin-freeswitch sh -c '
tail -c 6M /var/log/freeswitch/freeswitch.log 2>/dev/null | grep -E "skykin_outbound|Executing bridge|Ring-Ready|Ringing|PROCEEDING|180|183|200 OK|api_on_answer|uuid_record" | tail -60
'"""
    )
)

print("==== 4) last outbound CDR (start vs answer) ====")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT
  to_char(start_stamp AT TIME ZONE 'Africa/Addis_Ababa', 'HH24:MI:SS') AS start_eat,
  to_char(answer_stamp AT TIME ZONE 'Africa/Addis_Ababa', 'HH24:MI:SS') AS answer_eat,
  EXTRACT(EPOCH FROM (COALESCE(answer_stamp, end_stamp) - start_stamp))::int AS sec_to_answer_or_end,
  caller_id_number, destination_number, billsec, duration, hangup_cause
FROM v_xml_cdr
WHERE LOWER(COALESCE(direction,'')) = 'outbound'
  AND (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::date = CURRENT_DATE
ORDER BY start_stamp DESC
LIMIT 12;
"
"""
    )
)

c.close()
print("DONE")
