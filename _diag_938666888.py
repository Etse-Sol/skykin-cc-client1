#!/usr/bin/env python3
"""Diagnose no-audio inbound: 251938666888 ~14:46."""
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


def run(cmd, timeout=120):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print("==== server time ====")
print(run("date; timedatectl 2>/dev/null | head -4"))

print("==== CDR 938666888 ====")
sql = (
    "SELECT start_stamp, answer_stamp, end_stamp, direction, caller_id_number, "
    "destination_number, hangup_cause, billsec, duration, uuid, bridge_uuid "
    "FROM v_xml_cdr WHERE caller_id_number LIKE '%938666888%' "
    "OR destination_number LIKE '%938666888%' "
    "ORDER BY start_stamp DESC LIMIT 10;"
)
print(
    run(
        "docker exec skykin-postgres psql -U fusionpbx -d fusionpbx -c "
        + repr(sql)
    )
)

print("==== FS log lines with 938666888 (last 50) ====")
print(
    run(
        'docker exec skykin-freeswitch sh -c '
        '"grep -n 938666888 /var/log/freeswitch/freeswitch.log | tail -50"'
    )
)

print("==== recent inbound around 14:4x ====")
print(
    run(
        'docker exec skykin-freeswitch sh -c '
        '"grep -E \\"14:4[4-9]|14:5[0-2]\\" /var/log/freeswitch/freeswitch.log | '
        "grep -E '938666888|skykin_inbound|ANSWERED|Channel Answer|"
        "BRIDGE|Codec|Remote SDP|Local SDP|audio|rtp|SOFTPHONE|"
        "sofia/internal|sofia/external|CNG|MUTE|HOLD' | tail -120\""
    )
)

c.close()
