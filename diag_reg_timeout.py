import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "systemctl is-active skykin-ws-sip; systemctl status skykin-ws-sip --no-pager -l | head -25",
    "ss -lntup | grep -E '18081|5060|5080|8088' || netstat -lntup | grep -E '18081|5060|5080|8088'",
    "docker exec skykin-web grep -n 'wss\\|18081\\|proxy_pass' /etc/nginx/sites-enabled/skykin.conf /etc/nginx/conf.d/* 2>/dev/null | head -40",
    "journalctl -u skykin-ws-sip -n 60 --no-pager",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'",
    "docker ps --format 'table {{.Names}}\t{{.Status}}' | head -20",
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
