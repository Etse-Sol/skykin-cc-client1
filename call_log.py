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


print("==== recordings directory state ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'ls -ld /var/lib/freeswitch/recordings /var/lib/freeswitch/recordings/client1.skykin.local "
    "/var/lib/freeswitch/recordings/client1.skykin.local/archive 2>&1; echo ---; "
    "find /var/lib/freeswitch/recordings -type f -newermt \"-3 hours\" 2>/dev/null | head'"
    " | sed 's/^/  /'"
))

print("==== log: record_session / write errors ====")
print(run(
    "docker logs --since 60m skykin-freeswitch 2>&1 | "
    "grep -aiE 'record_session|Error opening|Cannot open|failed to open|permission denied|mkdir' "
    "| tail -20 | sed 's/^/  /'"
) or "  (no record_session activity logged)")

print("==== log: codec + media negotiation on the trunk leg ====")
print(run(
    "docker logs --since 60m skykin-freeswitch 2>&1 | "
    "grep -aiE 'Codec Activity|set codec|Audio Codec|PCMA|PCMU|OPUS.*8000|Original read|Set 200 OK|remote_media|Local SDP|Remote SDP' "
    "| tail -40 | sed 's/^/  /'"
) or "  (nothing)")

print("==== log: RTP problems ====")
print(run(
    "docker logs --since 60m skykin-freeswitch 2>&1 | "
    "grep -aiE 'rtp timeout|media timeout|no rtp|Jitter|dtls|srtp|invalid rtp|discarding|Bridge Failed|BREAK|zrtp' "
    "| tail -30 | sed 's/^/  /'"
) or "  (nothing)")

print("==== log: the 10:34 connected call (b6201c5c) ====")
print(run(
    "docker logs --since 60m skykin-freeswitch 2>&1 | grep -a 'b6201c5c' | head -60 | sed 's/^/  /'"
) or "  (that call is no longer in the log buffer)")
c.close()
