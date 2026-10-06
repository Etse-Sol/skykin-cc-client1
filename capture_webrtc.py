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


print("==== interfaces (which one holds the public IP) ====")
print(run("ip -4 -o addr show | sed 's/^/  /'"))

run("pkill tcpdump >/dev/null 2>&1; rm -f /tmp/webrtc.pcap")
# Media between the agent's browser and FreeSWITCH: RTP range, excluding the
# carrier network so we only see the WebRTC side.
run(
    "nohup timeout 300 tcpdump -s 0 -nni any "
    "'udp and portrange 16384-16584 and not net 10.208.233.0/24' "
    "-w /tmp/webrtc.pcap 2>/dev/null & echo ok"
)
time.sleep(3)
print("tcpdump running: " + run("pgrep -c tcpdump").strip())
print("\nCapture armed. Place a call and SPEAK for ~10 seconds.")
c.close()
