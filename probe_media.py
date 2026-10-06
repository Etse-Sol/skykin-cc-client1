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


print("==== is 5080/udp (external profile) forwarded into the container? ====")
print(run("docker port skykin-freeswitch | grep -aE '^(5080|5060)/' | sed 's/^/  /'"))

print("==== what the external profile is bound to ====")
print(run(r"""docker exec skykin-freeswitch fs_cli -x "sofia status" 2>&1 | sed 's/^/  /' """))

print("==== newest recordings on disk (last 90 min) ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'find /var/lib/freeswitch/recordings -name \"*.wav\" -mmin -90 -printf \"%TH:%TM %s %p\\n\" 2>/dev/null | sort'"
    " | sed 's/^/  /'"
))

print("==== FreeSWITCH log: did it see the carrier INVITE at 10:42? ====")
print(run(
    "docker logs --since 25m skykin-freeswitch 2>&1 | grep -aiE "
    "\"10.208.233.134|recv 1621|INVITE sip|acl|Rejected|unauthorized|no such|cannot locate|883|not found\" "
    "| tail -40 | sed 's/^/  /'"
))
c.close()
