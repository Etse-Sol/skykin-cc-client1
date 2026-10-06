#!/usr/bin/env python3
"""Diagnose SIP 500 outbound to 945184650."""
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
    timeout=30,
    allow_agent=False,
    look_for_keys=False,
)


def run(cmd, timeout=120):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== CDR 945184650 / recent outbound ====")
print(
    run(
        """docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT start_stamp AT TIME ZONE 'Africa/Addis_Ababa' AS eat,
       caller_id_number, destination_number, direction, billsec, duration,
       hangup_cause, sip_hangup_disposition, bridge_uuid, xml_cdr_uuid,
       left(COALESCE(hangup_cause_q850::text,''),20) AS q850,
       left(COALESCE(last_arg,''),100) AS last_arg
FROM v_xml_cdr
WHERE start_stamp AT TIME ZONE 'Africa/Addis_Ababa'
        BETWEEN '2026-09-29 12:20:00' AND '2026-09-29 12:35:00'
  AND (destination_number LIKE '%945184650%' OR destination_number LIKE '%940120143%'
       OR caller_id_number LIKE '202')
ORDER BY start_stamp DESC
LIMIT 15;
"
"""
    )
)

uuid = run(
    """docker exec skykin-db psql -U fusionpbx -d fusionpbx -tAc "
SELECT xml_cdr_uuid||'|'||COALESCE(bridge_uuid,'')
FROM v_xml_cdr
WHERE destination_number LIKE '%945184650%'
ORDER BY start_stamp DESC LIMIT 1;
"
"""
).strip()
print("UUID:", uuid)
a = uuid.split("|")[0] if uuid else ""
b = uuid.split("|")[1] if "|" in uuid else ""

if a:
    print("==== A-leg ====")
    print(
        run(
            f"""docker exec skykin-freeswitch sh -c '
grep -n "{a}" /var/log/freeswitch/freeswitch.log \\
| grep -iE "outbound|bridge|originate|Hangup|cause|500|503|480|486|ERROR|NO_|UNALLOC|GATEWAY|sofia/|ANSWER|CANCEL" \\
| tail -80
'"""
        )
    )
if b:
    print("==== B-leg ====")
    print(
        run(
            f"""docker exec skykin-freeswitch sh -c '
grep -n "{b}" /var/log/freeswitch/freeswitch.log \\
| grep -iE "Hangup|cause|500|503|480|486|sofia/|ANSWER|183|200|BYE|ERROR|GATEWAY" \\
| tail -50
'"""
        )
    )

print("==== FS log search by number/time ====")
print(
    run(
        r"""docker exec skykin-freeswitch sh -c '
grep -E "2026-09-29 09:2[0-9].*945184650|2026-09-29 09:3[0-2].*945184650|skykin outbound.*945184650|SIP 500|500 Internal" \
  /var/log/freeswitch/freeswitch.log | tail -40
grep -E "2026-09-29 09:2[5-9].*945184650|2026-09-29 09:3[0-2].*user/202" \
  /var/log/freeswitch/freeswitch.log | tail -40
'"""
    )
)

c.close()
print("DONE")
