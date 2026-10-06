#!/usr/bin/env python3
"""Diagnose 2026-09-29 12:17 outbound one-way audio (202 -> 940120143)."""
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


def run(cmd, timeout=120):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== 1) CDR ====")
print(
    run(
        """docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT start_stamp AT TIME ZONE 'Africa/Addis_Ababa' AS eat,
       answer_stamp AT TIME ZONE 'Africa/Addis_Ababa' AS ans,
       caller_id_number, destination_number, direction, billsec, duration,
       hangup_cause, bridge_uuid, xml_cdr_uuid,
       record_path, record_name,
       left(COALESCE(last_arg,''),140) AS last_arg
FROM v_xml_cdr
WHERE start_stamp AT TIME ZONE 'Africa/Addis_Ababa'
        BETWEEN '2026-09-29 12:15:00' AND '2026-09-29 12:20:00'
  AND (destination_number LIKE '%940120143%' OR caller_id_number LIKE '%202%')
ORDER BY start_stamp;
"
"""
    )
)

# Pull UUID from a simpler query
uuid_out = run(
    """docker exec skykin-db psql -U fusionpbx -d fusionpbx -tAc "
SELECT xml_cdr_uuid||'|'||COALESCE(bridge_uuid,'')||'|'||COALESCE(record_path,'')||'|'||COALESCE(record_name,'')
FROM v_xml_cdr
WHERE start_stamp AT TIME ZONE 'Africa/Addis_Ababa'
        BETWEEN '2026-09-29 12:15:00' AND '2026-09-29 12:20:00'
  AND destination_number LIKE '%940120143%'
ORDER BY start_stamp DESC LIMIT 1;
"
"""
).strip()
print("UUID row:", uuid_out)
parts = uuid_out.split("|") if uuid_out else []
a_uuid = parts[0] if parts else ""
b_uuid = parts[1] if len(parts) > 1 else ""
rec_path = parts[2] if len(parts) > 2 else ""
rec_name = parts[3] if len(parts) > 3 else ""

if a_uuid:
    print("==== 2) A-leg key lines ====")
    print(
        run(
            f"""docker exec skykin-freeswitch sh -c '
grep -n "{a_uuid}" /var/log/freeswitch/freeswitch.log \\
| grep -iE "outbound|pre_answer|bridge|ANSWER|Hangup|cause|AUDIO RTP|DTLS|Codec|Remote SDP|Local SDP|sofia/|ignore_early|rtp_advertise|READ|WRITE|jitter|packet|ERROR" \\
| tail -100
'"""
        )
    )
    if b_uuid:
        print("==== 3) B-leg key lines ====")
        print(
            run(
                f"""docker exec skykin-freeswitch sh -c '
grep -n "{b_uuid}" /var/log/freeswitch/freeswitch.log \\
| grep -iE "ANSWER|Hangup|cause|AUDIO RTP|Codec|sofia/|183|180|200|BYE|READ|WRITE|packet" \\
| tail -60
'"""
            )
        )

print("==== 4) Recording presence + sox stats ====")
if rec_path and rec_name:
    rec = f"{rec_path.rstrip('/')}/{rec_name}"
    print(
        run(
            f"""docker exec skykin-freeswitch sh -c '
ls -la "{rec}" 2>/dev/null || ls -la "{rec_path}"/*940* 2>/dev/null; ls -la "{rec_path}/{a_uuid}"* 2>/dev/null
if command -v sox >/dev/null 2>&1; then
  sox "{rec}" -n stats 2>&1 | head -40
  sox "{rec}" -n remix 1 stats 2>&1 | head -15
  sox "{rec}" -n remix 2 stats 2>&1 | head -15
elif command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -i "{rec}" -af astats -f null - 2>&1 | grep -E "Channel|RMS|Peak|Mean" | head -40
else
  file "{rec}" 2>/dev/null
  # try host sox
  true
fi
'"""
        )
    )
    print(
        run(
            f"""ls -la '{rec}' 2>/dev/null; sox '{rec}' -n stats 2>&1 | head -40; echo '--- L ---'; sox '{rec}' -n remix 1 stats 2>&1 | head -12; echo '--- R ---'; sox '{rec}' -n remix 2 stats 2>&1 | head -12"""
        )
    )
else:
    print(
        run(
            f"""find /var/lib/freeswitch/recordings/ahununu/archive/2026/Sep/29 -name '*{a_uuid}*' 2>/dev/null; ls -lt /var/lib/freeswitch/recordings/ahununu/archive/2026/Sep/29 | head -20"""
        )
    )

print("==== 5) live outbound.lua bridge line ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "'grep -nE \"ignore_early|rtp_advertise|pre_answer|bridge|media_webrtc|rtp_secure\" "
        "/etc/freeswitch/scripts/skykin_outbound.lua | head -40'"
    )
)

c.close()
print("DONE")
