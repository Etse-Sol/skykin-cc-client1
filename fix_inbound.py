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


print("==== existing inbound DID dialplan ====")
print(run("docker exec skykin-freeswitch cat /etc/freeswitch/dialplan/public/00_inbound_did.xml 2>&1 | sed 's/^/  /'"))

BR = "br-094746f74dd8"
FS = "172.22.0.3"

print("==== adding the missing 5080/udp forwarding into the container ====")
# Mirror exactly what Docker generates for a published UDP port. Without these two
# rules the carrier's INVITEs reach the host and are dropped, which is why they
# retransmit unanswered.
for tbl, rule in (
    ("nat", f"DOCKER ! -i {BR} -p udp -m udp --dport 5080 -j DNAT --to-destination {FS}:5080"),
    ("filter", f"DOCKER -d {FS}/32 ! -i {BR} -o {BR} -p udp -m udp --dport 5080 -j ACCEPT"),
):
    t = "-t nat " if tbl == "nat" else ""
    exists = run(f"iptables {t}-S DOCKER 2>/dev/null | grep -c -- '--dport 5080'").strip()
    if exists != "0":
        print(f"  {tbl}: rule already present")
        continue
    print(run(f"iptables {t}-I {rule} 2>&1 && echo '  {tbl}: rule added' || echo '  {tbl}: FAILED'"))

print("==== verify ====")
print(run("iptables -t nat -S DOCKER 2>/dev/null | grep -a 5080 | sed 's/^/  nat    /'"))
print(run("iptables -S DOCKER 2>/dev/null | grep -a 5080 | sed 's/^/  filter /'"))
c.close()
