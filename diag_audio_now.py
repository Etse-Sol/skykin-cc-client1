import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "journalctl -u skykin-ws-sip --since '8 min ago' --no-pager | grep -E 'INVITE|183|180|200|BYE|480|090|2519'",
    r"""docker exec skykin-freeswitch sh -c "grep -n '0902925776\|+251902925776\|AMR\|skykin_outbound' /var/log/freeswitch/freeswitch.log | tail -50" """,
    "ls -lt /root/skykin-fs-etc/dialplan/default/00_skykin.xml",
    "grep -n 'AMR\\|answer\\|bridge data' /root/skykin-fs-etc/dialplan/default/00_skykin.xml | head -20",
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
