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


print("==== gw / regs / agents ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status gateway SIP'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | cut -d'|' -f1,5,6"))
print(run("docker exec skykin-freeswitch fs_cli -x 'callcenter_config queue list' | head -3"))

print("==== last inbound / public / 488 / did ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E 'INVITE sip:\\\\+?25111113875|Processing .*11113875|"
        "skykin_inbound|mod_callcenter|Member |Originate |488|INCOMPATIBLE|"
        "NO_USER_RESPONSE|RECOVERY_ON_TIMER|DESTINATION_OUT|"
        "sofia/external/anonymous|public' "
        "/var/log/freeswitch/freeswitch.log | tail -80\""
    )
)
print("==== did xml ====")
print(run("cat /root/skykin-fs-etc/dialplan/public/01_skykin_did.xml"))
c.close()
