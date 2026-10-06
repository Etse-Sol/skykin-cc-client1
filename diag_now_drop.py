import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "journalctl -u skykin-ws-sip -n 40 --no-pager",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status gateway SIP'",
    r"""docker exec skykin-freeswitch sh -c "ls -lt /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/*.wav | head -8" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n 'sofia/gateway/SIP\\|INVITE sip:+251111138755\\|public\\|8000\\|NORMAL\\|NO_ROUTE\\|DESTINATION\\|Hangup' /var/log/freeswitch/freeswitch.log | tail -50" """,
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
