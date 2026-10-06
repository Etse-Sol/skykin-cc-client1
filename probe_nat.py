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


print("==== does docker-proxy hold the RTP ports on the host? ====")
print(run("ss -lnup 2>/dev/null | grep -aE ':(16384|16400|16402|16452)\\b' | sed 's/^/  /'"))
print("  docker-proxy count on RTP range: " + run(
    "ss -lnup 2>/dev/null | awk '{print $5}' | grep -oE ':1(63|64|65)[0-9][0-9]$' | wc -l"
).strip())

print("==== userland-proxy setting ====")
print(run("docker info 2>/dev/null | grep -aiE 'userland|native.overlay' | sed 's/^/  /'"))
print(run("cat /etc/docker/daemon.json 2>/dev/null | sed 's/^/  /'"))

print("==== NAT rules that touch RTP / 5080 ====")
print(run("iptables -t nat -S 2>/dev/null | grep -aE '16400|16384|5080' | head -20 | sed 's/^/  /'"))
print("  MASQUERADE rules for the skykin bridge:")
print(run("iptables -t nat -S POSTROUTING 2>/dev/null | grep -a '172.22.0.0' | sed 's/^/    /'"))

print("==== host route to the carrier ====")
print(run("ip route get 10.208.233.134 2>&1 | sed 's/^/  /'"))
print(run("ip route get 10.208.233.197 2>&1 | sed 's/^/  /'"))

print("==== leftover UDP conntrack entries in the RTP range (evidence of past calls) ====")
print(run(
    "(conntrack -L 2>/dev/null || cat /proc/net/nf_conntrack 2>/dev/null) "
    "| grep -aE '10.208.233' | head -20 | sed 's/^/  /'"
))
c.close()
