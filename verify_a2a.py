import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "systemctl is-active skykin-ws-sip",
    "grep -n pending_fs_via /etc/skykin/skykin_ws_sip.py | head",
    "docker exec skykin-web grep -n proxy_pass /etc/nginx/sites-enabled/skykin.conf",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'",
    "docker exec skykin-freeswitch fs_cli -x 'sofia_contact */102@client1.skykin.local'",
    "docker exec skykin-freeswitch fs_cli -x 'sofia_contact */103@client1.skykin.local'",
    "journalctl -u skykin-ws-sip -n 30 --no-pager",
]
for cmd in cmds:
    print("====", cmd)
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
