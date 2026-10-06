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


def run(cmd, timeout=120):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


# Passive background capture of ALL traffic to/from the carrier network for 180s.
# nohup + & so it keeps running after this SSH session closes.
run("pkill tcpdump >/dev/null 2>&1; rm -f /tmp/audio_test.txt /tmp/audio_test.pcap")
run(
    "nohup timeout 180 tcpdump -qnni any 'udp and net 10.208.233.0/24' "
    "> /tmp/audio_test.txt 2>/dev/null & echo started"
)
run(
    "nohup timeout 180 tcpdump -s 0 -nni any 'udp and net 10.208.233.0/24' "
    "-w /tmp/audio_test.pcap 2>/dev/null & echo started2"
)

print("Capture running for 180 seconds.")
print(run("sleep 2; pgrep -c tcpdump | sed 's/^/  tcpdump processes: /'"))
print(run('docker exec skykin-freeswitch fs_cli -x "show channels count" 2>&1 | sed "s/^/  channels now: /"'))
c.close()
