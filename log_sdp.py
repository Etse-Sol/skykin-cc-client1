import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=250):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


L = "/var/log/freeswitch/freeswitch.log"

print("==== the 200 OK FreeSWITCH received for the outbound call, with SDP ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'grep -a -n \"939777880\" {L} | tail -3'"
    " | sed 's/^/  /'"
))

print("==== remote SDP FreeSWITCH acted on (audio media address it will send to) ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'tail -60000 {L} 2>/dev/null' | "
    "grep -aE 'Remote SDP|remote_media_ip|Audio params|set to |Set 200 OK|sdp_audio' "
    "| tail -25 | sed 's/^/  /'"
))

print("==== all c=/m= lines FreeSWITCH logged in the last minutes (siptrace) ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'tail -60000 {L} 2>/dev/null' | "
    "grep -aE '^(c=IN|m=audio)|c=IN IP4|m=audio ' | tail -40 | sed 's/^/  /'"
))

print("==== what did FreeSWITCH consider the far-end media address? ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'tail -60000 {L} 2>/dev/null' | "
    "grep -aiE 'Starting media|Audio RTP [Ss]ession|rtp_session|Activating Audio|local host|Remote Address' "
    "| tail -20 | sed 's/^/  /'"
))
c.close()
