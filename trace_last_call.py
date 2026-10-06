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


def run(cmd, timeout=250):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


print("==== calls in the last 15 minutes ====")
print(run(
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -A -F' | ' -c "
    "\"SELECT start_stamp, direction, caller_id_number, destination_number, billsec, hangup_cause "
    "FROM v_xml_cdr WHERE start_stamp > now() - interval '15 minutes' "
    "ORDER BY start_stamp DESC LIMIT 10;\" 2>&1 | sed 's/^/  /'"
))

L = "/var/log/freeswitch/freeswitch.log"

print("==== the WebRTC leg f244da4b: what was it bridged to? ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'grep -a f244da4b {L} 2>/dev/null' | "
    "grep -aiE 'New Channel|Bridg|Set Codec|answer|hangup|destination|originate|callcenter' "
    "| head -25 | sed 's/^/  /'"
))

print("==== clean per-flow media view (browser side) ====")
print(run(
    "tcpdump -r /tmp/webrtc.pcap -qnn -tt 2>/dev/null | grep -aoE '[0-9.]+\\.[0-9]+ > [0-9.]+\\.[0-9]+' "
    "| sort | uniq -c | sort -rn | head -12 | sed 's/^/  /'"
))

print("==== why is no recording file appearing? ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'grep -a -A 3 \"record_session(/var\" {L} 2>/dev/null | tail -40'"
    " | sed 's/^/  /'"
))
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'ls -la /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/12/ 2>&1' | sed 's/^/  /'"
))
c.close()
