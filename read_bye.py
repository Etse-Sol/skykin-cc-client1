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


print("==== full SIP exchange incl. BYE headers and Reason ====")
print(run(
    "tcpdump -r /tmp/carrier.pcap -A -s0 -nn 'port 5060' 2>/dev/null "
    "| grep -aE '^[0-9]{2}:[0-9]{2}:[0-9]{2}|^(INVITE|BYE|ACK|PRACK|UPDATE) |^SIP/2\\.0 |"
    "^(Reason|Session-Expires|Require|Supported|Min-SE|Warning|X-|P-Early|Content-Length|Contact|To|From):' "
    "| sed 's/^/  /' | head -100"
))

print("\n==== our SDP offer on the most recent outbound call ====")
print(run(
    "tcpdump -r /tmp/carrier.pcap -A -s0 -nn 'port 5060' 2>/dev/null "
    "| grep -aE '^(v=0|o=|c=IN|m=audio|a=rtpmap|a=sendrecv|a=ptime|a=direction)' | head -30 | sed 's/^/  /'"
))

print("\n==== call durations from the CDR (is 20s consistent?) ====")
print(run(
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -A -F' | ' -c "
    "\"SELECT start_stamp, destination_number, duration, billsec, hangup_cause, "
    "sip_hangup_disposition FROM v_xml_cdr WHERE start_stamp > now() - interval '20 minutes' "
    "ORDER BY start_stamp DESC LIMIT 12;\" 2>&1 | sed 's/^/  /'"
))
c.close()
