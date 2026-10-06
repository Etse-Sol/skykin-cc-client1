#!/usr/bin/env python3
import paramiko
import sys

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
cmds = [
    r"""docker exec skykin-freeswitch sh -c 'grep -E "skykin welcome|skykin inbound try|after hours" /var/log/freeswitch/freeswitch.log | tail -25'""",
    "docker exec skykin-freeswitch cat /etc/freeswitch/scripts/skykin_welcome.lua",
    "docker exec skykin-freeswitch sed -n '1,50p' /etc/freeswitch/scripts/skykin_inbound.lua",
    r"""docker exec skykin-freeswitch sh -c 'printenv | grep -E "FS_USE_HOURS|FS_WELCOME|FS_CLOSED" || true'""",
    "docker exec skykin-freeswitch file /var/lib/freeswitch/recordings/ahununu/ahununu-opening.wav",
]
for cmd in cmds:
    print("====", cmd[:100], "====")
    _, o, e = c.exec_command(cmd, timeout=30)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
