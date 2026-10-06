import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "sed -n '238055,238140p' /var/log/freeswitch/freeswitch.log" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n '4257d123' /var/log/freeswitch/freeswitch.log | grep -iE 'Hangup complete|bytes|Packet|Quality|jitter|loss|SRTP|auth|discard|Invalid|stun|ICE' " """,
    r"""docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | head -20""",
    r"""docker exec skykin-freeswitch sh -c "sed -n '238110,238155p' /var/log/freeswitch/freeswitch.log" """,
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
