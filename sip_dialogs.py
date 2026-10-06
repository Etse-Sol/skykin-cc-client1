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


print("==== SIP messages with direction, method and SDP media lines ====")
print(run(
    "tcpdump -r /tmp/call.pcap -A -s0 -nn 'port 5060 or port 5080' 2>/dev/null "
    "| grep -aE '^[0-9]{2}:[0-9]{2}:[0-9]{2}|^(INVITE|ACK|BYE|CANCEL|PRACK|UPDATE|OPTIONS|REGISTER) |^SIP/2\\.0 |^(c=IN|m=audio|o=)' "
    "| sed 's/^/  /' | head -120"
))

print("==== is the 5080 DNAT rule actually being hit? (packet counters) ====")
print(run("iptables -t nat -L DOCKER -n -v --line-numbers 2>/dev/null | grep -aE 'pkts|5080' | head -5 | sed 's/^/  /'"))
print(run("iptables -L DOCKER -n -v 2>/dev/null | grep -a 5080 | sed 's/^/  /'"))
print("  external profile bind inside container:")
print(run("docker exec skykin-freeswitch sh -c 'ss -lnup 2>/dev/null | grep -a 5080' | sed 's/^/    /'"))
c.close()
