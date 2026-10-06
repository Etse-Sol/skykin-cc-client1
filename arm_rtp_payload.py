import sys
import time
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


run("pkill tcpdump >/dev/null 2>&1; rm -f /tmp/carrier.pcap")
# Carrier RTP is plain PCMA, so the payload can be decoded straight from the
# capture. That proves whether the packets we send hold the agent's voice or
# silence, without relying on anyone listening.
run(
    "nohup timeout 600 tcpdump -s 0 -nni enp4s3 'udp and net 10.208.233.0/24' "
    "-w /tmp/carrier.pcap 2>/dev/null & echo ok"
)
time.sleep(3)
print("tcpdump running: " + run("pgrep -c tcpdump").strip())
print("Carrier capture armed for 10 minutes.")
c.close()
