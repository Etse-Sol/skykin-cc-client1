import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "sed -n '221620,221670p' /var/log/freeswitch/freeswitch.log" """,
    "docker exec skykin-freeswitch sh -c 'grep -n enable-100rel /etc/freeswitch/sip_profiles/external.xml'",
    "ls -l /root/skykin-fs-etc/dialplan/default/00_ethio_mobile.xml /root/skykin-fs-etc/dialplan/default/00_skykin.xml",
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
