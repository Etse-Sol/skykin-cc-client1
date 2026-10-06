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


run("pkill tcpdump >/dev/null 2>&1; rm -f /tmp/call.pcap /tmp/call.txt")

# Full packet capture of everything to/from the carrier for 5 minutes: SDP tells
# us which media address each side promised, RTP tells us who actually sent audio.
run(
    "nohup timeout 300 tcpdump -s 0 -nni enp4s3 'net 10.208.233.0/24' "
    "-w /tmp/call.pcap 2>/dev/null & echo ok"
)
run(
    "nohup timeout 300 tcpdump -U -qnni enp4s3 'net 10.208.233.0/24' "
    "> /tmp/call.txt 2>/dev/null & echo ok2"
)
time.sleep(3)
print("tcpdump processes running: " + run("pgrep -c tcpdump").strip())

# SIP trace on the trunk profile so the negotiated SDP lands in the log too.
print(run('docker exec skykin-freeswitch fs_cli -x "sofia profile external siptrace on" 2>&1 | sed "s/^/  siptrace: /"'))
print(run('docker exec skykin-freeswitch fs_cli -x "console loglevel debug" 2>&1 | sed "s/^/  loglevel: /"'))
print("\nCapture armed for 5 minutes. Place ONE call now.")
c.close()
