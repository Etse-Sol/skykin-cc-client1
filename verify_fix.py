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


print("==== capture alive? ====")
print(run("pgrep -c tcpdump 2>&1 | sed 's/^/  tcpdump processes: /'"))
print(run("ls -l /tmp/call.pcap 2>&1 | sed 's/^/  /'"))

print("==== RTP direction in the current capture ====")
ours = run("tcpdump -r /tmp/call.pcap -qnn 'udp and not port 5060 and src 10.0.0.93' 2>/dev/null | wc -l").strip()
theirs = run("tcpdump -r /tmp/call.pcap -qnn 'udp and not port 5060 and src net 10.208.233.0/24' 2>/dev/null | wc -l").strip()
print(f"  RTP packets we sent:      {ours}")
print(f"  RTP packets carrier sent: {theirs}")

print("==== calls since the media fix ====")
print(run(
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -A -F' | ' -c "
    "\"SELECT start_stamp, destination_number, billsec, hangup_cause FROM v_xml_cdr "
    "WHERE start_stamp > now() - interval '12 minutes' ORDER BY start_stamp DESC LIMIT 6;\" 2>&1 | sed 's/^/  /'"
))

print("==== recordings written since the fix (stereo: agent + carrier) ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'find /var/lib/freeswitch/recordings -name \"*.wav\" -newermt \"-20 minutes\" -printf \"%s %p\\n\" 2>/dev/null'"
    " | sed 's/^/  /'"
) or "  (none yet)")
c.close()
