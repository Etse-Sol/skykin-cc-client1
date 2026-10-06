import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "ss -lntup | grep -E '18081|5060|5080|8088|python' || true",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status'",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal'",
    r"""docker exec skykin-freeswitch sh -c "grep -n 'REGISTER\\|401 Unauthorized\\|102@' /var/log/freeswitch/freeswitch.log | tail -40" """,
    "docker exec skykin-freeswitch fs_cli -x 'show channels count'",
    "tail -20 /etc/skykin/skykin_ws_sip.py | head -5; grep -n '5060\\|sendto\\|FS_\\|udp' /etc/skykin/skykin_ws_sip.py | head -40",
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
