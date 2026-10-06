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


print("==== capture file ====")
print(run("ls -l /tmp/webrtc.pcap 2>&1 | sed 's/^/  /'"))
print(run("pgrep -c tcpdump 2>&1 | sed 's/^/  tcpdump running: /'"))

print("==== media flows between browser(s) and FreeSWITCH ====")
print(run(
    "tcpdump -r /tmp/webrtc.pcap -qnn 2>/dev/null "
    "| awk '{print $3\" -> \"$5}' | sed 's/:$//' | sort | uniq -c | sort -rn | head -25 | sed 's/^/  /'"
) or "  (no browser media captured at all)")

print("==== totals by direction ====")
print("  browser -> server (inbound to us):  " + run(
    "tcpdump -r /tmp/webrtc.pcap -qnn 'dst 172.22.0.3 or dst 196.189.236.140' 2>/dev/null | wc -l"
).strip())
print("  server -> browser (outbound):       " + run(
    "tcpdump -r /tmp/webrtc.pcap -qnn 'src 172.22.0.3 or src 196.189.236.140' 2>/dev/null | wc -l"
).strip())

print("==== stereo recordings now written? ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'find /var/lib/freeswitch/recordings -name \"*.wav\" -newermt \"-25 minutes\" -printf \"%TH:%TM %s %p\\n\" 2>/dev/null | sort'"
    " | sed 's/^/  /'"
) or "  (none)")

print("==== recent opus decoder stats (frames received from browsers) ====")
print(run(
    "docker exec skykin-freeswitch sh -c 'tail -30000 /var/log/freeswitch/freeswitch.log 2>/dev/null' | "
    "grep -aE 'Opus (decoder|encoder) stats' | tail -12 | sed 's/^/  /'"
) or "  (none)")
c.close()
