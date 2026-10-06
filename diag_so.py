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


def run(cmd, timeout=80):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print(run("date -u"))
print(run("docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | cut -d'|' -f1,6,7"))
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep 'Processing Anonymous' /var/log/freeswitch/freeswitch.log | tail -5\""
    )
)
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E '14:4[3-9]|14:5' /var/log/freeswitch/freeswitch.log | "
        "grep -E 'joining queue|answered|LOSE_RACE|NO_USER|On Break|Receiving|"
        "New Channel sofia/internal' | tail -40\""
    )
)
c.close()
