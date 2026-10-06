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


def run(cmd, timeout=200):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


print("==== docker version (rule layout differs by version) ====")
print(run("docker --version 2>&1 | sed 's/^/  /'"))

print("==== NAT rules Docker made for a WORKING published udp port (16400) ====")
print(run("iptables -t nat -S 2>/dev/null | grep -a '16400' | sed 's/^/  /'"))

print("==== FILTER rules Docker made for that port ====")
print(run("iptables -S 2>/dev/null | grep -a '16400' | sed 's/^/  /'") or "  (none: filter accepts via a generic rule)")

print("==== generic DOCKER / DOCKER-FORWARD filter chains ====")
print(run("iptables -S DOCKER 2>/dev/null | head -15 | sed 's/^/  /'"))
print(run("iptables -S DOCKER-FORWARD 2>/dev/null | head -15 | sed 's/^/  /'"))

print("==== gateway context (where inbound trunk calls land) ====")
print(run(r"""docker exec skykin-freeswitch grep -aE "context" /etc/freeswitch/sip_profiles/external/SIP.xml | sed 's/^/  /' """))

print("==== is there ANY route for the DID in the public context? ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'ls /etc/freeswitch/dialplan/public/ 2>/dev/null; echo ---; "
    "grep -rl \"251111138755\" /etc/freeswitch/dialplan/ 2>/dev/null'"
    " | sed 's/^/  /'"
))
print("  public context extensions:")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'grep -ahoE \"extension name=\\\"[^\\\"]+\\\"\" /etc/freeswitch/dialplan/public/*.xml 2>/dev/null'"
    " | sed 's/^/    /'"
))
c.close()
