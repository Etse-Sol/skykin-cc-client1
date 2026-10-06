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


def run(cmd, timeout=60):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print("==== ufw ====")
print(run("ufw status verbose 2>&1 | head -40"))
print("==== iptables udp/rtp ====")
print(run("iptables -L INPUT -n -v | head -40"))
print(run("iptables -L OUTPUT -n -v | head -20"))
print(run("iptables -t nat -L POSTROUTING -n -v | head -20"))
print("==== last call rtp + pcap ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E 'AUDIO RTP|Processing 102 ' /var/log/freeswitch/freeswitch.log | tail -15\""
    )
)
print(run("ls -l /tmp/ethio.pcap /tmp/ethio-rtp.pcap 2>&1"))
print(
    run(
        "tcpdump -nn -r /tmp/ethio.pcap -c 20 2>/dev/null | head -20; "
        "echo '--- counts ---'; "
        "tcpdump -nn -r /tmp/ethio.pcap 2>/dev/null | awk "
        "'/10.0.0.93/ && /10.208.233/ { "
        "  if ($0 ~ /10.0.0.93.[0-9]+ > 10.208.233/) out++; "
        "  if ($0 ~ /10.208.233.[0-9]+.[0-9]+ > 10.0.0.93/) inn++; "
        "} END { print \"to_ethio\",out+0,\"from_ethio\",inn+0 }'"
    )
)
c.close()
