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


print("==== capture status ====")
print(run("pgrep -c tcpdump 2>&1 | sed 's/^/  tcpdump still running: /'"))
print(run("ls -l /tmp/call.pcap /tmp/call.txt 2>&1 | sed 's/^/  /'"))
print(run("wc -l < /tmp/call.txt 2>&1 | sed 's/^/  text lines captured: /'"))

print("==== did any call happen? (INVITE / RTP in the window) ====")
print(run("grep -acE 'INVITE|SIP' /tmp/call.txt 2>&1 | sed 's/^/  sip-ish lines: /'"))
print(run("awk '{print $2, $3, $4, $5, $6, $7}' /tmp/call.txt 2>/dev/null | sort | uniq -c | sort -rn | head -15 | sed 's/^/  /'"))

print("==== any outbound calls recorded since the fixes? ====")
print(run(
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -A -F' | ' -c "
    "\"SELECT start_stamp, destination_number, billsec, hangup_cause FROM v_xml_cdr "
    "WHERE start_stamp > now() - interval '40 minutes' ORDER BY start_stamp DESC LIMIT 10;\" 2>&1 | sed 's/^/  /'"
))
c.close()
