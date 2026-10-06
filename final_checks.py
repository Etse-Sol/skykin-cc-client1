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

print("==== full rtpmap list of the newest inbound offer (is 116 telephone-event?) ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'grep -a \"2e872d9c\" {L} | grep -aE \"a=rtpmap|m=audio|a=fmtp\"' "
    "| tail -25 | sed 's/^/  /'"
))

print("==== did the outbound 200 OK move the media to a new port? ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'sed -n \"/11:32:59/,/11:33:00/p\" {L} 2>/dev/null' "
    "| grep -aE 'c=IN|m=audio|Remote SDP|Audio params|unchanged|Changing' | head -20 | sed 's/^/  /'"
))

print("==== is RTCP enabled on the trunk profile? ====")
print(run(
    r"""docker exec skykin-freeswitch grep -aE "rtcp" /etc/freeswitch/sip_profiles/external.xml | sed 's/^/  /' """
) or "  RTCP not configured on the external profile")

print("==== agent-side transmit level vs carrier level (is our audio too quiet?) ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'tail -60000 {L} 2>/dev/null' | "
    "grep -aiE 'Set 200 OK|Changing Codec|Audio params are unchanged|Changing audio|reinvite' "
    "| tail -12 | sed 's/^/  /'"
))
c.close()
