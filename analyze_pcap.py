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


print("==== packet counts per flow (who sent audio to whom) ====")
# Non-5060 UDP on the carrier network is RTP. Grouping by src->dst shows the
# direction of media unambiguously.
print(run(
    "tcpdump -r /tmp/call.pcap -qnn 'udp and not port 5060' 2>/dev/null "
    "| awk '{print $3\" -> \"$5}' | sed 's/:$//' | sort | uniq -c | sort -rn | head -25 | sed 's/^/  /'"
) or "  NO RTP AT ALL in the capture")

print("==== total RTP packets: ours vs theirs ====")
print("  from us (10.0.0.93):   " + run(
    "tcpdump -r /tmp/call.pcap -qnn 'udp and not port 5060 and src 10.0.0.93' 2>/dev/null | wc -l"
).strip())
print("  from carrier:          " + run(
    "tcpdump -r /tmp/call.pcap -qnn 'udp and not port 5060 and src net 10.208.233.0/24' 2>/dev/null | wc -l"
).strip())

print("\n==== SDP: what media address/port each side promised ====")
print(run(
    "tcpdump -r /tmp/call.pcap -A -s0 -nn 'port 5060' 2>/dev/null "
    "| grep -aE '^(c=IN|m=audio|a=rtpmap|o=)' | sort | uniq -c | sort -rn | head -30 | sed 's/^/  /'"
))

print("==== SIP dialog summary for the 37s call ====")
print(run(
    "tcpdump -r /tmp/call.pcap -A -s0 -nn 'port 5060' 2>/dev/null "
    "| grep -aoE '^(INVITE|ACK|BYE|CANCEL|PRACK|SIP/2\\.0 [0-9]{3})[^\\r]*' "
    "| sort | uniq -c | sort -rn | head -20 | sed 's/^/  /'"
))

print("==== ICMP errors from the carrier (port unreachable = they are not listening) ====")
print(run("tcpdump -r /tmp/call.pcap -qnn 'icmp' 2>/dev/null | head -15 | sed 's/^/  /'") or "  (none)")
c.close()
