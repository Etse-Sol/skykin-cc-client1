import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "sed -n '233229,233380p' /var/log/freeswitch/freeswitch.log" """,
    "echo '==== default files ===='",
    "docker exec skykin-freeswitch sh -c 'ls -l /etc/freeswitch/dialplan/default/; echo ---; grep -l del-group /etc/freeswitch/dialplan/*.xml /etc/freeswitch/dialplan/default/*.xml 2>/dev/null'",
    "echo '==== queue ===='",
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config queue list'",
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list'",
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
