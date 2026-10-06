#!/usr/bin/env python3
"""SkyKin call-path health check on ecs-cc."""
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect(
        "196.189.236.140",
        port=30,
        username="root",
        password="Pass@1234",
        timeout=20,
        allow_agent=False,
        look_for_keys=False,
    )
except Exception as e:
    print("SSH_FAIL", type(e).__name__, e)
    sys.exit(2)


def run(cmd, timeout=120):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== containers ====")
print(run("docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'NAMES|skykin'"))

print("==== FS process / ESL ====")
print(run("docker exec skykin-freeswitch sh -c 'ps aux | grep freeswitch | grep -v grep | head -3'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'status' 2>&1 | head -15"))

print("==== registrations (ahununu) ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg' 2>&1 | grep -E 'User:|Contact:|ahununu|Status' | head -40"))

print("==== live channels / calls ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'show channels count' 2>&1"))
print(run("docker exec skykin-freeswitch fs_cli -x 'show calls count' 2>&1"))

print("==== agents queue 8000@ahununu ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'callcenter_config queue list agents 8000@ahununu' 2>&1 | head -20"))

print("==== inbound/outbound scripts markers ====")
print(run("docker exec skykin-freeswitch sh -c 'grep -c \"ALWAYS WebRTC\\|retry once\\|skykin_qwait\\|tone_stream\" /etc/freeswitch/scripts/skykin_inbound.lua /etc/freeswitch/scripts/skykin_outbound.lua 2>/dev/null'"))
print(run("docker exec skykin-freeswitch ls -la /etc/freeswitch/scripts/skykin_biz_hours_off 2>&1"))

print("==== today CDR summary (Addis) ====")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT
  COUNT(*) FILTER (WHERE LOWER(direction)='inbound' AND destination_number ~ '11619803') AS inbound_did,
  COUNT(*) FILTER (WHERE LOWER(direction)='outbound') AS outbound,
  COUNT(*) FILTER (WHERE hangup_cause='NORMAL_TEMPORARY_FAILURE') AS temp_fail,
  COUNT(*) FILTER (WHERE hangup_cause='ORIGINATOR_CANCEL' AND LOWER(direction)='outbound') AS out_cancel
FROM v_xml_cdr
WHERE (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::date = CURRENT_DATE;
"
"""
    )
)

print("==== last 8 reportable-ish rows ====")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT to_char(start_stamp AT TIME ZONE 'Africa/Addis_Ababa', 'HH24:MI') AS t,
  caller_id_number, destination_number, direction, billsec, hangup_cause
FROM v_xml_cdr
WHERE (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::date = CURRENT_DATE
  AND destination_number ~ '11619803|^(9|0)[0-9]{8}$|^(1|2)[0-9]{2}$'
ORDER BY start_stamp DESC LIMIT 8;
"
"""
    )
)

print("==== softphone fail markers (recent log) ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "'tail -c 4000000 /var/log/freeswitch/freeswitch.log 2>/dev/null "
        "| grep -E \"skykin softphone_fail|queue wait VISIBLE|TEMPORARY_FAILURE|skykin_outbound ringback\" "
        "| tail -25'"
    )
)

c.close()
print("DONE")
