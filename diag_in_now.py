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


print("==== now ====")
print(run("date -u; docker exec skykin-freeswitch fs_cli -x 'sofia status gateway SIP' | grep -E 'State|Status|CallsIN'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg' | grep -E 'User:|Status:|IP:'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | cut -d'|' -f1,5,6,7"))

print("==== last inbound after 14:33 ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E '14:3[3-9]|14:4' /var/log/freeswitch/freeswitch.log | "
        "grep -E 'anonymous|skykin_inbound|Member |Agent |Originate |"
        "New Channel sofia/internal/10|INVITE sip:10|488|487|NO_ANSWER|"
        "INCOMPATIBLE|Receiving|abandoned|joining queue' | tail -80\""
    )
)
print("==== last public processing ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep 'Processing .*->' /var/log/freeswitch/freeswitch.log | tail -15\""
    )
)
c.close()
