#!/usr/bin/env python3
"""Verify Answer fix (always media_webrtc) is live on ecs-cc."""
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect(
        "196.189.236.140",
        username="root",
        password="Pass@1234",
        timeout=20,
        allow_agent=False,
        look_for_keys=False,
    )
except Exception as e:
    print("SSH_FAIL", type(e).__name__, e)
    sys.exit(2)


def run(cmd, timeout=90):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== 1) host script has ALWAYS WebRTC / media_webrtc=true ====")
print(
    run(
        "grep -n 'ALWAYS WebRTC\\|media_webrtc=true\\|sip-udp\\|UDP-vs-WebRTC\\|bridge webrtc\\|bridge sip' "
        "/opt/skykin/docker/freeswitch/scripts/skykin_inbound.lua "
        "/opt/skykin/app/docker/freeswitch/scripts/skykin_inbound.lua "
        "2>/dev/null | head -40"
    )
)

print("==== 2) container live script (what FreeSWITCH actually runs) ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c '"
        "grep -n \"ALWAYS WebRTC\\|media_webrtc=true\\|media_webrtc=false\\|bridge webrtc\\|sip-udp\\|UDP-vs\" "
        "/etc/freeswitch/scripts/skykin_inbound.lua | head -40'"
    )
)

print("==== 3) recent bridge mode in FS log (after noon) ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c '"
        "grep -E \"skykin bridge (webrtc|sip-udp)|ALWAYS|inbound cause=NORMAL_TEMPORARY\" "
        "/var/log/freeswitch/freeswitch.log 2>/dev/null | tail -40'"
    )
)

print("==== 4) temp_fail count since 12:30 vs before ====")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -t -c "
SELECT 'before_fix_1030_1230' AS window,
  COUNT(*) FILTER (WHERE hangup_cause='NORMAL_TEMPORARY_FAILURE') AS temp_fail
FROM v_xml_cdr
WHERE (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::date = CURRENT_DATE
  AND (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::time BETWEEN '10:30' AND '12:30'
UNION ALL
SELECT 'after_fix_1230_1830',
  COUNT(*) FILTER (WHERE hangup_cause='NORMAL_TEMPORARY_FAILURE')
FROM v_xml_cdr
WHERE (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::date = CURRENT_DATE
  AND (start_stamp AT TIME ZONE 'Africa/Addis_Ababa')::time BETWEEN '12:30' AND '18:30';
"
"""
    )
)

print("==== 5) last 10 bridge webrtc lines with time ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c '"
        "grep \"skykin bridge webrtc\" /var/log/freeswitch/freeswitch.log 2>/dev/null | tail -10'"
    )
)

c.close()
print("DONE")
