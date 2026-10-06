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


def run(cmd):
    _, o, e = c.exec_command(cmd)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print("==== container net ====")
print(run("docker inspect skykin-freeswitch --format '{{.HostConfig.NetworkMode}} {{.HostConfig.Privileged}}'"))
print(run("docker exec skykin-freeswitch sh -c 'ip -4 addr | grep inet'"))
print("==== last FS webrtc SDP IPs ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E 'c=IN IP4|a=candidate:|AUDIO RTP|Local SDP sofia/internal' "
        "/var/log/freeswitch/freeswitch.log | grep -E '196\\.|10\\.0\\.|172\\.' | tail -30\""
    )
)
c.close()
