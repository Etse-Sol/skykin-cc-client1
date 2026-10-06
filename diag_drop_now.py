import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "journalctl -u skykin-ws-sip --since '5 min ago' --no-pager",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'",
    "docker exec skykin-freeswitch sh -c \"tail -n 200 /var/log/freeswitch/freeswitch.log | grep -E 'INVITE|180|200 OK|ACK|BYE|480|487|503|hangup|DESTROY|sofia/internal/10[123]|NORMAL_|INCOMPATIBLE|CODEC|sdp' | tail -80\"",
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
