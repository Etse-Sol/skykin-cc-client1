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


def run(cmd, timeout=90):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print("==== now ====")
print(run("date -u"))
print(run("docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | cut -d'|' -f1,5,6,7"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))

print("==== last 102 originate detail ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E '962n92op|user/102|102@client1|031ab55a' /var/log/freeswitch/freeswitch.log | "
        "grep -E '14:3[7-9]|14:4' | "
        "grep -E 'New Channel|INVITE|Local SDP|Remote SDP|Codec|488|487|480|408|"
        "NO_USER|INCOMPATIBLE|PRE_ANSWER|Ring|180|183|200|Hangup|CANCEL|"
        "media_webrtc|sofia.c:7493|Callstate' | tail -100\""
    )
)
c.close()
