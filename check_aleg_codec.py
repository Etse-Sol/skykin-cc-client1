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


print("==== freeswitch log file present? ====")
print(run("docker exec skykin-freeswitch sh -c 'ls -l /var/log/freeswitch/ 2>&1 | head' | sed 's/^/  /'"))

L = "/var/log/freeswitch/freeswitch.log"
print("==== codec negotiation on the agent (WebRTC) leg ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'tail -20000 {L} 2>/dev/null' | "
    "grep -aiE 'Codec Activity|set codec|opus|transcoding|Raw Codec|native' | tail -30 | sed 's/^/  /'"
) or "  (nothing)")

print("==== transcoding / decode errors ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'tail -20000 {L} 2>/dev/null' | "
    "grep -aiE 'cannot decode|decode error|no decoder|codec.*fail|Failure|switch_rtp.*error|invalid|srtp|dtls' "
    "| tail -30 | sed 's/^/  /'"
) or "  (nothing)")

print("==== record_session outcome ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'tail -20000 {L} 2>/dev/null' | "
    "grep -aiE 'record_session|Error opening|Cannot open' | tail -15 | sed 's/^/  /'"
) or "  (nothing)")

print("==== media stats for the most recent bridged call ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'tail -4000 {L} 2>/dev/null' | "
    "grep -aiE 'Bridge|audio_in|audio_out|packet_count|Hangup.*NORMAL' | tail -20 | sed 's/^/  /'"
) or "  (nothing)")
c.close()
