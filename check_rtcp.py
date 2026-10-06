import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "docker exec skykin-freeswitch sh -c \"grep -nE 'rtcp|rtp-timeout' /etc/freeswitch/sip_profiles/external.xml\"",
    r"""docker exec skykin-freeswitch sh -c "grep -n 'f16b094e' /var/log/freeswitch/freeswitch.log | grep -iE 'rtcp|Auto Changing|AMR|error|fail|warn' | tail -30" """,
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
